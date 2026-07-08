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
    mocker.patch('virtual_device.rename_cable_output', return_value=True)
    result = vbcable_setup.install()
    assert result is True
    args, kwargs = mock_run.call_args
    assert args[0][0] == 'powershell'
    assert str(installer) in args[0][-1]
    assert kwargs.get('timeout') == 120


def test_install_returns_false_when_installer_missing(mocker):
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value='C:/nonexistent.exe')
    mocker.patch('vbcable_setup._download_installer', side_effect=Exception('no network'))
    assert vbcable_setup.install() is False


def test_install_calls_progress_callback(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=0)
    mocker.patch('virtual_device.rename_cable_output', return_value=True)
    messages = []
    vbcable_setup.install(progress_callback=messages.append)
    assert len(messages) == 2
    assert any('VB-Cable' in m for m in messages)
    assert any('áudio' in m for m in messages)


def test_install_calls_rename_on_success(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=0)
    mock_rename = mocker.patch('virtual_device.rename_cable_output', return_value=True)

    vbcable_setup.install()

    mock_rename.assert_called_once()


def test_install_does_not_rename_on_failure(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=1)
    mock_rename = mocker.patch('virtual_device.rename_cable_output', return_value=True)

    vbcable_setup.install()

    mock_rename.assert_not_called()
