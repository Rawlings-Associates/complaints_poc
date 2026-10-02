"""Minimal UniCourt DEEP API client (standard library only)."""

from __future__ import annotations

import collections
import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

API_ROOT = "https://deep-api.unicourt.com"

# UniCourt allows 30 requests per 5 seconds per account and answers 429 beyond
# that. The limit is also counted per endpoint; one shared limiter across all
# endpoints satisfies both. Rate-limited calls are not billable, so retrying
# them costs nothing.
RATE_LIMIT_CALLS = 30
RATE_LIMIT_PERIOD = 5.0
RATE_LIMITED_RETRIES = 6  # 429s are retried separately from server errors

# Transient server-side failures worth retrying (429 is handled on its own).
_RETRYABLE = {500, 502, 503, 504}


class RateLimiter:
    """At most ``calls`` requests in any rolling ``period`` seconds, across threads.

    ``pause(seconds)`` holds every caller back, used when the API answers 429
    anyway (another process sharing the key, clock differences).
    """

    def __init__(self, calls: int = RATE_LIMIT_CALLS, period: float = RATE_LIMIT_PERIOD,
                 clock=time.monotonic, sleep=time.sleep):
        self.calls = calls
        self.period = period
        self.clock = clock
        self.sleep = sleep
        self.waited = 0.0  # total seconds callers spent waiting
        self._stamps: collections.deque[float] = collections.deque()
        self._not_before = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self.clock()
                while self._stamps and now - self._stamps[0] >= self.period:
                    self._stamps.popleft()
                wait = self._not_before - now
                if wait <= 0 and len(self._stamps) < self.calls:
                    self._stamps.append(now)
                    return
                if wait <= 0:
                    wait = self.period - (now - self._stamps[0])
                self.waited += wait
            self.sleep(wait)

    def pause(self, seconds: float) -> None:
        with self._lock:
            self._not_before = max(self._not_before, self.clock() + seconds)


class UniCourtError(RuntimeError):
    """An error response from the API, carrying UniCourt's Exception body."""

    def __init__(self, status: int, code: str = "", message: str = "", details: str = ""):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"HTTP {status} {code} {message}: {details}".strip())


def _ssl_context() -> ssl.SSLContext:
    """Honour the CA bundle env vars that corporate/agent proxies rely on."""
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and Path(path).is_file():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


class UniCourtClient:
    """Authenticated requests scoped to one workspace.

    Paths starting with ``/workspace/`` or another absolute API path are used
    as given (``nextPageAPI`` links come back that way); anything else is
    prefixed with ``/workspace/{workspace_id}``.
    """

    def __init__(
        self,
        token: str,
        workspace_id: str,
        root: str = API_ROOT,
        timeout: float = 60,
        retries: int = 3,
        verbose: bool = False,
        limiter: RateLimiter | None = None,
        on_unauthorized=None,
    ):
        self.token = token
        # Called once when the API answers 401: returns a replacement token, or
        # None to give up. Used to replace a stored token that was revoked.
        self.on_unauthorized = on_unauthorized
        self._auth_lock = threading.Lock()
        self.workspace_id = workspace_id
        self.root = root.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.verbose = verbose
        self.requests_made = 0
        self.rate_limited = 0  # 429 responses received
        self._count_lock = threading.Lock()
        self.limiter = limiter or RateLimiter()
        self._ctx = _ssl_context()

    # -- plumbing ---------------------------------------------------------

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        if path.startswith("http"):
            url = path
        elif path.startswith("/"):
            url = self.root + path
        else:
            url = f"{self.root}/workspace/{self.workspace_id}/{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(clean)
        return url

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[api] {msg}", file=sys.stderr)

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        url = self._url(path, params)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        attempt = throttled = 0
        refreshed = False
        while True:
            token_used = self.token
            if auth:
                headers["Authorization"] = f"Bearer {token_used}"
            self.limiter.acquire()
            self._log(f"{method} {url}")
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            with self._count_lock:
                self.requests_made += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                    return json.loads(resp.read() or b"{}")
            except urllib.error.HTTPError as exc:
                payload = _json_or_empty(exc.read())
                if exc.code == 401 and auth and self.on_unauthorized and not refreshed:
                    refreshed = True
                    if self._replace_token(token_used):
                        continue
                if _is_rate_limited(exc.code, payload) and throttled < RATE_LIMITED_RETRIES:
                    throttled += 1
                    with self._count_lock:
                        self.rate_limited += 1
                    wait = _retry_after(exc.headers.get("Retry-After"), self.limiter.period)
                    self._log(f"HTTP 429 rate limited, pausing all requests {wait:.1f}s")
                    self.limiter.pause(wait)
                    continue
                if exc.code in _RETRYABLE and attempt < self.retries:
                    attempt += 1
                    wait = 2 ** attempt
                    self._log(f"HTTP {exc.code}, retrying in {wait}s")
                    time.sleep(wait)
                    continue
                raise UniCourtError(
                    exc.code,
                    payload.get("code", ""),
                    payload.get("message", ""),
                    payload.get("details", exc.reason or ""),
                ) from None
            except urllib.error.URLError as exc:
                if attempt < self.retries:
                    attempt += 1
                    time.sleep(2 ** attempt)
                    continue
                raise UniCourtError(0, "NETWORK", "", str(exc.reason)) from None

    def _replace_token(self, rejected: str) -> bool:
        """Swap in a new token once, even when several workers hit 401 together."""
        with self._auth_lock:
            if self.token != rejected:  # another worker already replaced it
                return True
            new = self.on_unauthorized()
            if not new:
                return False
            self.token = new
            self._log("token was rejected (401); replaced it and retrying")
            return True

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("GET", path, params=params)

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", path, body=body)

    def paginate(
        self,
        path: str,
        array_key: str,
        params: dict[str, Any] | None = None,
        max_items: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield items across pages, starting at ``pageNumber=1``.

        List endpoints require ``pageNumber`` (a missing one is a 400), so it is
        always sent on the first request. If ``meta`` is given, it receives the
        first page's top-level fields (``totalCount``, ``totalPages``, ...).
        """
        page = self.get(path, {"pageNumber": 1, **(params or {})})
        if meta is not None:
            meta.update({k: v for k, v in page.items() if k not in (array_key, "data")})
        yield from self.iter_pages(page, array_key, max_items)

    def iter_pages(
        self, page: dict[str, Any], array_key: str, max_items: int | None = None
    ) -> Iterator[dict[str, Any]]:
        """Yield the items of ``page`` and every page after it.

        Follows ``nextPageAPI`` (the documented, reliable way) until it is null.
        It also stops on an empty page (asking past the last page returns an
        empty list, not an error) and on a link it has already followed.
        Items are read from ``array_key``, or ``data`` as the docs describe.
        """
        seen = 0
        visited: set[str] = set()
        while True:
            items = page.get(array_key)
            if items is None:
                items = page.get("data")
            if not items:
                return
            for item in items:
                yield item
                seen += 1
                if max_items is not None and seen >= max_items:
                    return
            nxt = page.get("nextPageAPI")
            if not nxt or nxt in visited:  # a repeated link would loop forever
                return
            visited.add(nxt)
            page = self.get(nxt)

    def fetch_file(self, url: str, dest: Path) -> int:
        """Download a signed file URL. No auth header: it is another host."""
        self._log(f"GET {url.split('?')[0]}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
            content = resp.read()
        dest.write_bytes(content)
        return len(content)


def _is_rate_limited(status: int, payload: dict[str, Any]) -> bool:
    """429, or either documented body: {"code": "UN429", ...} / {"message": "Too Many Requests"}."""
    message = str(payload.get("message", "")).replace("_", " ").strip().lower()
    return status == 429 or payload.get("code") == "UN429" or message == "too many requests"


def _retry_after(value: str | None, default: float) -> float:
    """Seconds from a Retry-After header (delta-seconds form), else ``default``."""
    try:
        seconds = float(value) if value else default
    except ValueError:
        seconds = default
    return min(max(seconds, 0.5), 60.0)


def _json_or_empty(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw or b"{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}
