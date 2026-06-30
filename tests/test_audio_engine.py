import numpy as np
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
