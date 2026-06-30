import logging
import threading
import sounddevice as sd
from noise_filter import NoiseFilter

SAMPLE_RATE = 48000
CHUNK_FRAMES = 960  # 20ms at 48kHz


class AudioEngine:
    def __init__(self):
        self._filter = NoiseFilter()
        self._stop_event = threading.Event()
        self._thread = None
        self._input_device = None
        self._intensity = 0.75

    def set_input_device(self, device_name: str):
        self._input_device = device_name

    def set_intensity(self, intensity: float):
        self._intensity = max(0.0, min(1.0, intensity))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        output_device = self._find_cable_input()
        if output_device is None:
            return
        try:
            with sd.Stream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=CHUNK_FRAMES,
                device=(self._input_device, output_device),
                callback=self._callback,
            ):
                self._stop_event.wait()
        except Exception:
            logging.exception("AudioEngine stream error")

    def _callback(self, indata, outdata, frames, time, status):
        chunk = indata[:, 0]
        filtered = self._filter.apply(chunk.copy(), self._intensity)
        outdata[:, 0] = filtered

    def _find_cable_input(self):
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if 'CABLE Input' in d['name'] and d['max_output_channels'] > 0:
                return i
        return None
