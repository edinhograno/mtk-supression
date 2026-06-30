import numpy as np

SAMPLE_RATE = 48000
CHUNK_SIZE = 960

try:
    import rnnoise as _rnnoise_lib
    _BACKEND = 'rnnoise'
except ImportError:
    _rnnoise_lib = None
    _BACKEND = 'noisereduce'


class NoiseFilter:
    def __init__(self):
        self._backend = _BACKEND
        if self._backend == 'rnnoise':
            self._denoiser = _rnnoise_lib.RNNoise()

    def apply(self, chunk: np.ndarray, intensity: float) -> np.ndarray:
        intensity = max(0.0, min(1.0, intensity))
        if intensity == 0.0:
            return chunk
        if self._backend == 'rnnoise':
            filtered = self._apply_rnnoise(chunk)
        else:
            filtered = self._apply_noisereduce(chunk)
        return chunk * (1.0 - intensity) + filtered * intensity

    def _apply_rnnoise(self, chunk: np.ndarray) -> np.ndarray:
        result = self._denoiser.process_frame(chunk.astype(np.float32))
        return np.array(result, dtype=np.float32)

    def _apply_noisereduce(self, chunk: np.ndarray) -> np.ndarray:
        import noisereduce as nr
        return nr.reduce_noise(y=chunk, sr=SAMPLE_RATE, stationary=True).astype(np.float32)

    @property
    def backend(self) -> str:
        return self._backend
