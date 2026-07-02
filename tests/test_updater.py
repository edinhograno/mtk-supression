import json
from pathlib import Path
from unittest.mock import patch, MagicMock


def _mock_urlopen(tag_name: str):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({'tag_name': tag_name}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_parse_version_strips_v_prefix():
    import updater
    assert updater._parse_version('v1.2.3') == [1, 2, 3]


def test_parse_version_no_prefix():
    import updater
    assert updater._parse_version('1.0.0') == [1, 0, 0]


def test_check_for_update_returns_version_when_newer(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', return_value=_mock_urlopen('v1.1.0'))
    with patch.object(updater, '__version__', '1.0.0'):
        result = updater.check_for_update()
    assert result == '1.1.0'


def test_check_for_update_returns_none_when_same(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', return_value=_mock_urlopen('v1.0.0'))
    with patch.object(updater, '__version__', '1.0.0'):
        result = updater.check_for_update()
    assert result is None


def test_check_for_update_returns_none_when_older(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', return_value=_mock_urlopen('v0.9.0'))
    with patch.object(updater, '__version__', '1.0.0'):
        result = updater.check_for_update()
    assert result is None


def test_check_for_update_returns_none_on_network_error(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', side_effect=Exception('network error'))
    result = updater.check_for_update()
    assert result is None


def test_download_update_calls_progress_cb(mocker, tmp_path):
    import updater
    dest = tmp_path / 'mtk-noise-canceller-setup.exe'
    progress_values = []

    def fake_urlretrieve(url, destpath, reporthook):
        reporthook(1, 500_000, 1_000_000)  # 50%
        reporthook(2, 500_000, 1_000_000)  # 100%
        return str(destpath), {}

    mocker.patch('urllib.request.urlretrieve', side_effect=fake_urlretrieve)
    mocker.patch('updater._temp_setup_path', lambda v: dest)

    updater.download_update('1.1.0', progress_values.append)
    assert 50 in progress_values
    assert 100 in progress_values


def test_download_update_returns_path(mocker, tmp_path):
    import updater
    dest = tmp_path / 'mtk-noise-canceller-setup.exe'
    mocker.patch('urllib.request.urlretrieve', return_value=(str(dest), {}))
    mocker.patch('updater._temp_setup_path', lambda v: dest)
    result = updater.download_update('1.1.0', lambda p: None)
    assert result == dest


def test_launch_installer_calls_popen(mocker):
    import updater
    mock_popen = mocker.patch('subprocess.Popen')
    p = Path('C:/temp/setup.exe')
    updater.launch_installer(p)
    mock_popen.assert_called_once_with([str(p)])
