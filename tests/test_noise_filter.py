import numpy as np
import pytest
from unittest.mock import patch, MagicMock

SAMPLE_RATE = 48000
CHUNK_SIZE = 960


def make_chunk():
    rng = np.random.default_rng(42)
    return rng.random(CHUNK_SIZE).astype(np.float32)


def test_passthrough_at_zero_intensity():
    from noise_filter import NoiseFilter
    f = NoiseFilter()
    chunk = make_chunk()
    result = f.apply(chunk.copy(), 0.0)
    np.testing.assert_array_equal(result, chunk)


def test_output_same_shape():
    from noise_filter import NoiseFilter
    f = NoiseFilter()
    chunk = make_chunk()
    result = f.apply(chunk, 0.75)
    assert result.shape == chunk.shape


def test_intensity_clipped_above_one():
    from noise_filter import NoiseFilter
    f = NoiseFilter()
    chunk = make_chunk()
    result_1 = f.apply(chunk.copy(), 1.0)
    result_2 = f.apply(chunk.copy(), 2.0)
    np.testing.assert_array_equal(result_1, result_2)


def test_intensity_clipped_below_zero():
    from noise_filter import NoiseFilter
    f = NoiseFilter()
    chunk = make_chunk()
    result_neg = f.apply(chunk.copy(), -1.0)
    result_zero = f.apply(chunk.copy(), 0.0)
    np.testing.assert_array_equal(result_neg, result_zero)


def test_backend_falls_back_to_noisereduce():
    with patch.dict('sys.modules', {'rnnoise': None}):
        import importlib
        import noise_filter
        importlib.reload(noise_filter)
        f = noise_filter.NoiseFilter()
        assert f.backend == 'noisereduce'


def test_backend_uses_rnnoise_when_available():
    mock_rnnoise = MagicMock()
    mock_denoiser = MagicMock()
    mock_rnnoise.RNNoise.return_value = mock_denoiser
    chunk = make_chunk()
    mock_denoiser.process_frame.return_value = chunk.tolist()
    with patch.dict('sys.modules', {'rnnoise': mock_rnnoise}):
        import importlib
        import noise_filter
        importlib.reload(noise_filter)
        f = noise_filter.NoiseFilter()
        assert f.backend == 'rnnoise'
