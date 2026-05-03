"""Background update check against GitHub Releases.

Per the v1 UX decision: this never prompts on startup. It just polls the
"latest release" endpoint in a daemon thread, and if a newer version exists it
stashes the info in module state. ``ui.py`` reads that state when the user
opens the panel and surfaces a small "update available" affordance there.

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
        try:
            req = Request(RELEASES_API, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except (URLError, ValueError, OSError):
            return  # silent — never block the user

        latest = data.get('tag_name')
        local = get_local_version()
        if not latest or not local:
            return

        if _parse_semver(latest) > _parse_semver(local):
            _pending_update = {
                'version': latest,
                'url': data.get('html_url', f'https://github.com/{REPO}/releases'),
            }

    threading.Thread(target=worker, daemon=True).start()


def get_pending_update() -> Optional[dict]:
    """Return ``{'version': 'v0.2.0', 'url': '...'}`` or None."""
    return _pending_update
