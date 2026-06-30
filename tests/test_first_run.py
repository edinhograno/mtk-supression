import pytest
from unittest.mock import patch, MagicMock, call


def make_config(first_run=True, autostart=False):
    c = MagicMock()
    c.get.side_effect = lambda k, default=None: {
        'first_run': first_run,
        'autostart': autostart,
    }.get(k, default)
    return c


def test_skips_when_not_first_run():
    config = make_config(first_run=False)
    from first_run import run_if_needed
    result = run_if_needed(config)
    assert result is True
    config.save.assert_not_called()


def test_returns_false_when_user_declines_vbcable(mocker):
    from importlib import reload
    import first_run
    reload(first_run)
    mocker.patch('vbcable_setup.is_installed', return_value=False)
    mocker.patch('first_run._ask_install_vbcable', return_value=False)
    config = make_config(first_run=True)
    result = first_run.run_if_needed(config)
    assert result is False


def test_returns_true_when_cable_already_installed(mocker):
    from importlib import reload
    import first_run
    reload(first_run)
    mocker.patch('vbcable_setup.is_installed', return_value=True)
    mocker.patch('first_run._ask_autostart', return_value=False)
    mocker.patch('first_run._set_autostart')
    config = make_config(first_run=True)
    result = first_run.run_if_needed(config)
    assert result is True
    config.set.assert_any_call('first_run', False)
    config.save.assert_called_once()


def test_sets_autostart_when_user_says_yes(mocker):
    from importlib import reload
    import first_run
    reload(first_run)
    mocker.patch('vbcable_setup.is_installed', return_value=True)
    mocker.patch('first_run._ask_autostart', return_value=True)
    mock_set_autostart = mocker.patch('first_run._set_autostart')
    config = make_config(first_run=True)
    first_run.run_if_needed(config)
    mock_set_autostart.assert_called_once_with(True)
    config.set.assert_any_call('autostart', True)


def test_returns_false_when_install_fails(mocker):
    from importlib import reload
    import first_run
    reload(first_run)
    mocker.patch('vbcable_setup.is_installed', return_value=False)
    mocker.patch('first_run._ask_install_vbcable', return_value=True)
    mocker.patch('vbcable_setup.install', return_value=False)
    mocker.patch('first_run._show_install_error')
    config = make_config(first_run=True)
    result = first_run.run_if_needed(config)
    assert result is False
