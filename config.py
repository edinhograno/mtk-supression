import json
from pathlib import Path
import sys

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
        self._data = {
            'first_run': True,
            'input_device': None,
            'intensity': 0.75,
            'autostart': False,
            'active': True,
        }
        self._load()

    def _load(self):
        config_module = sys.modules[__name__]
        config_file = config_module.CONFIG_FILE
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def save(self):
        config_module = sys.modules[__name__]
        config_dir = config_module.CONFIG_DIR
        config_file = config_module.CONFIG_FILE
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    def reload(self):
        self._data = {
            'first_run': True,
            'input_device': None,
            'intensity': 0.75,
            'autostart': False,
            'active': True,
        }
        self._load()
