import pytest
from unittest.mock import patch, MagicMock


def _devices_with_cable():
    return [
        {'name': 'CABLE Input (VB-Audio Virtual Cable)', 'max_input_channels': 0, 'max_output_channels': 2},
    ]


def _devices_without_cable():
    return [
        {'name': 'Microfone Realtek', 'max_input_channels': 1, 'max_output_channels': 0},
    ]


def test_is_installed_true_when_cable_present(mocker):
    mocker.patch('sounddevice.query_devices', return_value=_devices_with_cable())
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    assert vbcable_setup.is_installed() is True


def test_is_installed_false_when_cable_absent(mocker):
    mocker.patch('sounddevice.query_devices', return_value=_devices_without_cable())
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    assert vbcable_setup.is_installed() is False


def test_install_returns_true_on_success(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(returncode=0)
    result = vbcable_setup.install()
    assert result is True
    mock_run.assert_called_once_with([str(installer), '/S'], capture_output=True, timeout=60, cwd=str(tmp_path))


def test_install_returns_false_when_installer_missing(mocker):
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value='C:/nonexistent.exe')
    assert vbcable_setup.install() is False


def test_install_calls_progress_callback(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=0)
    messages = []
    vbcable_setup.install(progress_callback=messages.append)
    assert len(messages) == 1
    assert 'VB-Cable' in messages[0]
