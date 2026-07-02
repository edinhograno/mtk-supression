import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable

from version import __version__

_REPO = "edinhograno/mtk-supression"
_ASSET = "mtk-noise-canceller-setup.exe"
_API_URL = f"https://api.github.com/repos/{_REPO}/releases/latest"


def _parse_version(v: str) -> list[int]:
    return [int(x) for x in v.lstrip('v').split('.')]


def _temp_setup_path(version: str) -> Path:
    return Path(tempfile.gettempdir()) / _ASSET


def check_for_update() -> str | None:
    try:
        req = urllib.request.Request(_API_URL, headers={'User-Agent': 'mtk-noise-canceller'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        tag = data['tag_name']
        if _parse_version(tag) > _parse_version(__version__):
            return tag.lstrip('v')
        return None
    except Exception:
        return None


def download_update(version: str, progress_cb: Callable[[int], None]) -> Path:
    url = f"https://github.com/{_REPO}/releases/download/v{version}/{_ASSET}"
    dest = _temp_setup_path(version)

    def reporthook(block_count: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            pct = min(100, block_count * block_size * 100 // total_size)
            progress_cb(pct)

    urllib.request.urlretrieve(url, str(dest), reporthook)
    return dest


def launch_installer(setup_path: Path) -> None:
    subprocess.Popen([str(setup_path)])
