import numpy as np

SAMPLE_RATE = 48000
CHUNK_SIZE = 960

try:
    from pedalboard import Pedalboard, NoiseGate, HighpassFilter
    _BACKEND = 'pedalboard'
except ImportError:
    _BACKEND = 'noisereduce'


class NoiseFilter:
    def __init__(self):
        self._backend = _BACKEND
        if self._backend == 'pedalboard':
            self._gate = NoiseGate(threshold_db=-50, ratio=1.5, attack_ms=5, release_ms=100)
            self._board = Pedalboard([HighpassFilter(cutoff_frequency_hz=80), self._gate])

    def apply(self, chunk: np.ndarray, intensity: float) -> np.ndarray:
        intensity = max(0.0, min(1.0, intensity))
        if intensity == 0.0:
            return chunk
        if self._backend == 'pedalboard':
            return self._apply_pedalboard(chunk, intensity)
        return self._apply_noisereduce(chunk, intensity)

    def _apply_pedalboard(self, chunk: np.ndarray, intensity: float) -> np.ndarray:
        # intensity 0→-60dB (barely gates), 1→-35dB (aggressive)
        self._gate.threshold_db = -60.0 + intensity * 25.0
        processed = self._board(chunk[np.newaxis, :].astype(np.float32), SAMPLE_RATE)
        return processed[0]

    def _apply_noisereduce(self, chunk: np.ndarray, intensity: float) -> np.ndarray:
        import noisereduce as nr
        reduced = nr.reduce_noise(
            y=chunk, sr=SAMPLE_RATE, stationary=True, prop_decrease=intensity * 0.5
        ).astype(np.float32)
        return chunk * (1.0 - intensity * 0.5) + reduced * (intensity * 0.5)

    @property
    def backend(self) -> str:
        return self._backend
