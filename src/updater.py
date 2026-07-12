"""Background update check against GitHub Releases.

Per the v1 UX decision: this never prompts on startup. It just polls the
"latest release" endpoint in a daemon thread. If a newer version exists it
stashes the info in module state AND in a small cache file next to
version.json — the cache is what makes the result survive a Fusion restart.
``ui.py`` reads ``get_pending_update()`` during ``start()`` and registers the
"Update available" toolbar button if it returns something.

Why the cache file: ``start()`` fires the check and reads the result in the
same breath, so the fresh network result never arrives in time to register
the button in the session that fetched it. Module memory dies with Fusion,
so without a cache the button could never appear at all. The flow is:
session N's worker writes the cache → session N+1's ``start()`` reads it →
button registered. The worker deletes the cache when the local version has
caught up, so a stale "update available" can't outlive the update itself.

Failures are silent on purpose — a flaky network must not break Fusion startup
or the importer.
"""

import json
import os
import threading
from typing import Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO = 'cutaway-hq/fusion-addin'
RELEASES_API = f'https://api.github.com/repos/{REPO}/releases/latest'
USER_AGENT = 'Cutaway-Fusion-AddIn'

_TIMEOUT_SECONDS = 5
_pending_update: Optional[dict] = None
_check_started = False


def _addin_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cache_path() -> str:
    # Lives next to version.json in the per-user AddIns folder (user-writable).
    # Dot-prefixed + .gitignored so a dev-link junction doesn't dirty the repo.
    return os.path.join(_addin_root(), '.update_check.json')


def _read_cached_update() -> Optional[dict]:
    """Return a still-relevant cached check result, or None.

    Re-validates against the CURRENT local version — the user may have
    installed the update since the cache was written, and a stale
    "update available" for a version we're already on must not surface.
    """
    try:
        with open(_cache_path(), 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    version = data.get('version')
    local = get_local_version()
    if not version or not local:
        return None
    if _parse_semver(version) <= _parse_semver(local):
        return None
    return {
        'version': version,
        'url': data.get('url') or f'https://github.com/{REPO}/releases',
    }


def get_local_version() -> Optional[str]:
    """Read version.json bundled with the add-in. None if missing/malformed."""
    try:
        with open(os.path.join(_addin_root(), 'version.json'), 'r') as f:
            return json.load(f).get('version')
    except (OSError, ValueError, KeyError):
        return None


def _parse_semver(s: str) -> Tuple[int, int, int]:
    if s.startswith('v'):
        s = s[1:]
    parts = s.split('.')[:3]
    while len(parts) < 3:
        parts.append('0')
    try:
        return tuple(int(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return (0, 0, 0)


def check_in_background() -> None:
    """Fire-and-forget poll of GitHub Releases. Safe to call repeatedly."""
    global _check_started
    if _check_started:
        return
    _check_started = True

    def worker():
        global _pending_update
        # Everything inside the try: this module's contract is "failures are
        # silent" — an unexpected response shape (e.g. a non-dict JSON body)
        # must not traceback in the daemon thread either.
        try:
            req = Request(RELEASES_API, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            if not isinstance(data, dict):
                return
            latest = data.get('tag_name')
            local = get_local_version()
            if not latest or not local:
                return

            if _parse_semver(latest) > _parse_semver(local):
                _pending_update = {
                    'version': latest,
                    'url': data.get('html_url', f'https://github.com/{REPO}/releases'),
                }
                # Persist for the NEXT session — this session's UI was built
                # before the check finished (see module docstring).
                with open(_cache_path(), 'w', encoding='utf-8') as f:
                    json.dump(_pending_update, f)
            else:
                # Local version caught up — drop any stale cached prompt.
                try:
                    os.remove(_cache_path())
                except OSError:
                    pass
        except Exception:
            return  # silent — never block the user

    threading.Thread(target=worker, daemon=True).start()


def get_pending_update() -> Optional[dict]:
    """Return ``{'version': 'v0.2.0', 'url': '...'}`` or None.

    Falls back to the cache file written by a PREVIOUS session's check —
    on a fresh Fusion launch the in-memory result doesn't exist yet.
    """
    return _pending_update or _read_cached_update()
