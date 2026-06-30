import json
from pathlib import Path

# Only initialize if not already set (preserves patches during reload)
if 'CONFIG_DIR' not in dir():
    CONFIG_DIR = Path.home() / '.mtk-noise-canceller'
if 'CONFIG_FILE' not in dir():
    CONFIG_FILE = CONFIG_DIR / 'config.json'

_DEFAULTS = {
    'first_run': True,
    'input_device': None,
    'intensity': 0.75,
    'autostart': False,
    'active': True,
}


class Config:
    def __init__(self):
        self._data = dict(_DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    def reload(self):
        self._data = dict(_DEFAULTS)
        self._load()
