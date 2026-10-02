"""Workspace tokens: generated from the client ID and secret, stored privately.

The CLI exchanges ``UNICOURT_CLIENT_ID`` / ``UNICOURT_CLIENT_SECRET`` for a
workspace token (``POST /generateNewWorkspaceToken``) on first use and keeps it
in a file only the current user can read, so later runs reuse it. Tokens never
expire and a workspace may hold at most 10, so minting one per run would soon
hit that limit.

What is stored, per API root and workspace: the token, its token id, the
workspace id, when it was created, and a SHA-256 of the client id (to notice a
switch of credentials). The client secret is never written anywhere.

Location: ``$UNICOURT_CREDENTIALS_FILE``, else
``$XDG_CONFIG_HOME/unicourt/credentials.json``, else
``~/.config/unicourt/credentials.json`` (``%APPDATA%\\unicourt`` on Windows).
The directory is created 0700 and the file 0600; looser permissions on an
existing file are tightened with a warning.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import UniCourtClient, UniCourtError

FILE_VERSION = 1


def credentials_path() -> Path:
    explicit = os.environ.get("UNICOURT_CREDENTIALS_FILE")
    if explicit:
        return Path(explicit).expanduser()
    if os.name == "nt" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "unicourt" / "credentials.json"


def client_fingerprint(client_id: str) -> str:
    return hashlib.sha256(client_id.encode()).hexdigest()


def mask(token: str) -> str:
    return f"{token[:6]}…{token[-4:]}" if len(token) > 12 else "…"


class TokenStore:
    """The credentials file: entries keyed by API root and workspace."""

    def __init__(self, path: Path | None = None, warn=None):
        self.path = path or credentials_path()
        self.warn = warn or (lambda msg: print(msg, file=sys.stderr))

    @staticmethod
    def key(api_root: str, workspace_id: str) -> str:
        return f"{api_root.rstrip('/')}|{workspace_id}"

    # -- reading ---------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        self._tighten_permissions()
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.warn(f"Ignoring unreadable credentials file {self.path}")
            return {}
        entries = data.get("tokens") if isinstance(data, dict) else None
        return entries if isinstance(entries, dict) else {}

    def find(self, api_root: str, workspace_id: str | None = None,
             client_id: str | None = None) -> dict[str, Any] | None:
        """The stored entry for this root (and workspace, and client, when given).

        Without a workspace id, the single entry for this root is used; with
        several, the caller must say which workspace.
        """
        root = api_root.rstrip("/")
        candidates = [e for e in self._load().values()
                      if e.get("api_root") == root
                      and (workspace_id is None or e.get("workspace_id") == workspace_id)
                      and (client_id is None or e.get("client_id_sha256") == client_fingerprint(client_id))]
        if len(candidates) > 1 and workspace_id is None:
            ids = ", ".join(sorted(e["workspace_id"] for e in candidates))
            raise SystemExit(f"Tokens are stored for several workspaces ({ids}); "
                             "choose one with --workspace or UNICOURT_WORKSPACE.")
        return candidates[0] if candidates else None

    # -- writing ---------------------------------------------------------------

    def save(self, entry: dict[str, Any]) -> None:
        entries = self._load()
        entries[self.key(entry["api_root"], entry["workspace_id"])] = entry
        self._write(entries)

    def remove(self, api_root: str, workspace_id: str) -> None:
        entries = self._load()
        if entries.pop(self.key(api_root, workspace_id), None) is not None:
            self._write(entries)

    def _write(self, entries: dict[str, Any]) -> None:
        directory = self.path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != "nt":
            os.chmod(directory, 0o700)
        fd, tmp = tempfile.mkstemp(prefix=".credentials-", dir=directory)  # created 0600
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump({"version": FILE_VERSION, "tokens": entries}, fh, indent=2)
            if os.name != "nt":
                os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)  # atomic: never a half-written file
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def _tighten_permissions(self) -> None:
        if os.name == "nt":
            return
        mode = stat.S_IMODE(self.path.stat().st_mode)
        if mode & 0o077:
            os.chmod(self.path, 0o600)
            self.warn(f"Tightened permissions on {self.path} to 600 (they were {mode:o}).")


# -- talking to UniCourt ------------------------------------------------------------

def discover_workspace(make_api, client_id: str, client_secret: str, note=None) -> dict[str, Any]:
    """Find the workspace to use, so nobody has to look its id up.

    A temporary *account* token is created (``POST /generateNewToken``). Its
    response carries the account's DEEP workspace (``deepWorkspace``); if not,
    ``GET /workspaces`` is listed and the workspace of type ``DEEP`` is taken
    (or the only workspace, if there is just one). The account token is always
    revoked afterwards (``PUT /invalidateToken``) so it does not count against
    the account's 10-token limit.

    ``make_api(token)`` returns a ``UniCourtClient`` using that token.
    """
    note = note or (lambda _msg: None)
    api = make_api("")
    try:
        account = api.request("POST", "/generateNewToken", auth=False,
                              body={"clientId": client_id, "clientSecret": client_secret})
    except UniCourtError as exc:
        if exc.code == "UN203":
            raise SystemExit("The account already has the maximum of 10 account tokens, so the "
                             "workspace cannot be looked up. Revoke unused ones (UniCourt's "
                             "/listAllTokenIds and /invalidateToken) or set UNICOURT_WORKSPACE.") from None
        raise
    token_id = account.get("tokenId", "")
    try:
        workspace = account.get("deepWorkspace") or {}
        if workspace.get("workspaceId"):
            return workspace
        listing = make_api(account["accessToken"])
        workspaces = list(listing.paginate("/workspaces", "workspaceArray"))
        return _choose_workspace(workspaces)
    finally:
        try:
            api.request("PUT", "/invalidateToken", auth=False,
                        body={"clientId": client_id, "clientSecret": client_secret, "tokenId": token_id})
        except UniCourtError as exc:
            note(f"Could not revoke the temporary account token {token_id}: {exc}. "
                 "Revoke it in UniCourt to free the slot.")


def _choose_workspace(workspaces: list[dict[str, Any]]) -> dict[str, Any]:
    deep = [w for w in workspaces if str(w.get("workspaceType", "")).upper() == "DEEP"]
    if len(deep) == 1:
        return deep[0]
    if not deep and len(workspaces) == 1:
        return workspaces[0]
    if not workspaces:
        raise SystemExit("The account has no workspaces. Create one in UniCourt first.")
    listed = "\n".join(f"  {w.get('workspaceId')}  {w.get('workspaceType', '?'):<7} {w.get('workspaceName', '')}"
                       for w in workspaces)
    raise SystemExit("Could not pick a workspace automatically "
                     f"({len(deep)} of type DEEP). Choose one with UNICOURT_WORKSPACE or --workspace:\n{listed}")


def generate(api: UniCourtClient, client_id: str, client_secret: str, workspace_id: str) -> dict[str, Any]:
    """Create a workspace token and return the entry to store."""
    try:
        result = api.request(
            "POST", "/generateNewWorkspaceToken", auth=False,
            body={"clientId": client_id, "clientSecret": client_secret, "workspaceId": workspace_id},
        )
    except UniCourtError as exc:
        if exc.code == "UN203":
            raise SystemExit(
                f"Workspace {workspace_id} already has the maximum of 10 tokens. Revoke unused "
                "ones (UniCourt's /listAllWorkspaceTokenIds and /invalidateWorkspaceToken), "
                "then try again."
            ) from None
        raise
    return {
        "api_root": api.root,
        "workspace_id": result.get("workspaceId") or workspace_id,
        "token_id": result.get("workspaceTokenId", ""),
        "access_token": result["accessToken"],
        "client_id_sha256": client_fingerprint(client_id),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def revoke(api: UniCourtClient, client_id: str, client_secret: str, entry: dict[str, Any]) -> None:
    """Invalidate a stored workspace token with UniCourt."""
    api.request(
        "PUT", "/invalidateWorkspaceToken", auth=False,
        body={"clientId": client_id, "clientSecret": client_secret,
              "workspaceId": entry["workspace_id"], "workspaceTokenId": entry["token_id"]},
    )
