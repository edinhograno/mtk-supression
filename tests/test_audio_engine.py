import pytest
from unittest.mock import patch, MagicMock, call


def _mock_devices():
    return [
        {'name': 'Microfone Realtek', 'max_input_channels': 1, 'max_output_channels': 0},
        {'name': 'CABLE Input (VB-Audio Virtual Cable)', 'max_input_channels': 0, 'max_output_channels': 2},
    ]


def test_is_running_false_before_start():
    from audio_engine import AudioEngine
    e = AudioEngine()
    assert e.is_running() is False


def test_set_intensity_clamps():
    from audio_engine import AudioEngine
    e = AudioEngine()
    e.set_intensity(2.0)
    assert e._intensity == 1.0
    e.set_intensity(-0.5)
    assert e._intensity == 0.0


def test_set_input_device():
    from audio_engine import AudioEngine
    e = AudioEngine()
    e.set_input_device('Microfone Realtek')
    assert e._input_device == 'Microfone Realtek'


def test_find_cable_input_returns_index(mocker):
    mocker.patch('sounddevice.query_devices', return_value=_mock_devices())
    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    assert e._find_cable_input() == 1


def test_find_cable_input_returns_none_when_absent(mocker):
    mocker.patch('sounddevice.query_devices', return_value=[
        {'name': 'Microfone Realtek', 'max_input_channels': 1, 'max_output_channels': 0},
    ])
    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    assert e._find_cable_input() is None


def test_stop_after_never_started():
    from audio_engine import AudioEngine
    e = AudioEngine()
    e.stop()  # must not raise


def test_start_saves_prev_default_and_sets_mtk(mocker):
    mocker.patch('virtual_device.get_default_capture_id', return_value='prev-id')
    mocker.patch('virtual_device.find_device_id', return_value='mtk-id')
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    mocker.patch.object(e, '_run')  # prevent real audio thread
    e.start()
    e.stop()

    assert mock_set.call_args_list[0] == call('mtk-id')
    assert e._prev_default_id is None  # stop() cleared it


def test_stop_restores_previous_default(mocker):
    mocker.patch('virtual_device.get_default_capture_id', return_value='prev-id')
    mocker.patch('virtual_device.find_device_id', return_value='mtk-id')
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    mocker.patch.object(e, '_run')
    e.start()
    e.stop()

    # Last set_as_default_capture call must restore prev-id
    assert mock_set.call_args_list[-1] == call('prev-id')


def test_stop_without_start_does_not_restore(mocker):
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    e.stop()

    mock_set.assert_not_called()


def test_restart_without_stop_does_not_overwrite_prev_default(mocker):
    mocker.patch('virtual_device.get_default_capture_id', return_value='real-mic')
    mocker.patch('virtual_device.find_device_id', return_value='mtk-id')
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    mocker.patch.object(e, '_run')
    e.start()  # saves 'real-mic' as _prev_default_id
    # Simulate: thread died, _prev_default_id still set; now mock returns MTK as current default
    mocker.patch('virtual_device.get_default_capture_id', return_value='mtk-id')
    e.start()  # must NOT overwrite _prev_default_id
    e.stop()

    # Last restore call must be 'real-mic', not 'mtk-id'
    assert mock_set.call_args_list[-1] == call('real-mic')
