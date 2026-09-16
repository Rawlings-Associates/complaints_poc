"""Minimal CourtListener REST v4 client.

Built around a hard constraint: the account is limited to a small number of
requests per minute.  Every request therefore goes through a persistent token
bucket and an on-disk cache, so repeated runs of the CLI normally cost zero
requests.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

API_ROOT = "https://www.courtlistener.com/api/rest/v4"
DEFAULT_CACHE_DIR = Path(
    os.environ.get("MDL_CACHE_DIR", Path.home() / ".cache" / "mdl_complaints")
)


class CourtListenerError(RuntimeError):
    """Raised when the API returns something we cannot use."""


class RateLimitExceeded(CourtListenerError):
    """Raised when the API keeps throttling us after all retries."""


def _ssl_context() -> ssl.SSLContext:
    """Honour the CA bundle env vars that corporate/agent proxies rely on."""
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and Path(path).is_file():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


@dataclass
class TokenBucket:
    """Sliding-window limiter whose state survives process exit.

    The CLI is short-lived, so an in-memory limiter would let two back-to-back
    invocations blow the per-minute budget.  Timestamps are persisted instead.
    """

    max_calls: int
    period: float
    state_path: Path
    _stamps: list[float] = field(default_factory=list)

    def _load(self) -> list[float]:
        try:
            stamps = json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return []
        cutoff = time.time() - self.period
        return [s for s in stamps if isinstance(s, (int, float)) and s > cutoff]

    def _save(self, stamps: list[float]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(stamps))
        tmp.replace(self.state_path)

    def acquire(self, *, verbose: bool = False) -> None:
        stamps = self._load()
        if len(stamps) >= self.max_calls:
            wait = (stamps[0] + self.period) - time.time()
            if wait > 0:
                if verbose:
                    print(
                        f"  [rate-limit] {len(stamps)}/{self.max_calls} used; "
                        f"waiting {wait:.1f}s",
                        file=sys.stderr, flush=True,
                    )
                time.sleep(wait)
            stamps = self._load()
        stamps.append(time.time())
        self._save(stamps)

    def remaining(self) -> int:
        return max(0, self.max_calls - len(self._load()))


class CourtListenerClient:
    """Thin, dependency-free wrapper over the endpoints this tool needs."""

    def __init__(
        self,
        token: str | None = None,
        *,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        use_cache: bool = True,
        max_calls: int = 10,
        period: float = 60.0,
        verbose: bool = False,
        timeout: float = 60.0,
    ) -> None:
        self.token = token or os.environ.get("COURTLISTENER_API_KEY", "")
        if not self.token:
            raise CourtListenerError(
                "No API token. Set COURTLISTENER_API_KEY or pass --token."
            )
        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache
        self.verbose = verbose
        self.timeout = timeout
        self.request_count = 0
        self.cache_hits = 0
        self.bucket = TokenBucket(
            max_calls=max_calls,
            period=period,
            state_path=self.cache_dir / "rate_state.json",
        )
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=_ssl_context())
        )

    # -- cache ---------------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / "responses" / f"{sha256(url.encode()).hexdigest()}.json"

    def _read_cache(self, url: str) -> dict[str, Any] | None:
        if not self.use_cache:
            return None
        path = self._cache_path(url)
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None

    def _write_cache(self, url: str, payload: dict[str, Any]) -> None:
        path = self._cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(path)

    # -- http ----------------------------------------------------------------

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET a URL, returning parsed JSON. Cached and rate-limited."""
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        cached = self._read_cache(url)
        if cached is not None:
            self.cache_hits += 1
            if self.verbose:
                print(f"  [cache] {url}", file=sys.stderr, flush=True)
            return cached

        payload = self._fetch(url)
        self._write_cache(url, payload)
        return payload

    def _fetch(self, url: str, max_attempts: int = 5) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Token {self.token}",
                "Accept": "application/json",
                "User-Agent": "mdl-complaints-poc/0.1",
            },
        )
        for attempt in range(max_attempts):
            self.bucket.acquire(verbose=self.verbose)
            if self.verbose:
                print(f"  [GET] {url}", file=sys.stderr, flush=True)
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    self.request_count += 1
                    return json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                body = exc.read().decode(errors="replace")[:400]
                if exc.code == 429:
                    wait = float(exc.headers.get("Retry-After") or 2 ** (attempt + 1))
                    if self.verbose:
                        print(
                            f"  [429] throttled; sleeping {wait:.0f}s",
                            file=sys.stderr, flush=True,
                        )
                    time.sleep(min(wait, 120))
                    continue
                if exc.code in (401, 403):
                    raise CourtListenerError(
                        f"Auth failed ({exc.code}). Check COURTLISTENER_API_KEY. {body}"
                    ) from exc
                raise CourtListenerError(f"HTTP {exc.code} for {url}: {body}") from exc
            except urllib.error.URLError as exc:
                if attempt == max_attempts - 1:
                    raise CourtListenerError(f"Network error for {url}: {exc}") from exc
                time.sleep(2 ** attempt)
        raise RateLimitExceeded(
            f"Still throttled after {max_attempts} attempts: {url}"
        )

    # -- endpoints -----------------------------------------------------------

    def dockets(self, **params: Any) -> dict[str, Any]:
        return self.get(f"{API_ROOT}/dockets/", params)

    def docket_entries(self, **params: Any) -> dict[str, Any]:
        return self.get(f"{API_ROOT}/docket-entries/", params)
