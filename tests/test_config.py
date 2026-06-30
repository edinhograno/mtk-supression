import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_defaults_when_no_file(tmp_path):
    with patch('config.CONFIG_FILE', tmp_path / 'config.json'):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
    assert c.get('first_run') is True
    assert c.get('intensity') == 0.75
    assert c.get('active') is True
    assert c.get('autostart') is False
    assert c.get('input_device') is None


def test_load_existing_file(tmp_path):
    cfg_file = tmp_path / 'config.json'
    cfg_file.write_text(json.dumps({'intensity': 0.5, 'first_run': False}))
    with patch('config.CONFIG_FILE', cfg_file):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
    assert c.get('intensity') == 0.5
    assert c.get('first_run') is False
    assert c.get('active') is True  # default for key not in file


def test_set_and_save(tmp_path):
    cfg_file = tmp_path / 'config.json'
    with patch('config.CONFIG_FILE', cfg_file), patch('config.CONFIG_DIR', tmp_path):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
        c.set('intensity', 0.3)
        c.save()
    data = json.loads(cfg_file.read_text())
    assert data['intensity'] == 0.3


def test_corrupted_file_uses_defaults(tmp_path):
    cfg_file = tmp_path / 'config.json'
    cfg_file.write_text('not json')
    with patch('config.CONFIG_FILE', cfg_file):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
    assert c.get('intensity') == 0.75
