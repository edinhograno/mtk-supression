import logging
import threading
import sounddevice as sd
from noise_filter import NoiseFilter
import virtual_device

SAMPLE_RATE = 48000
CHUNK_FRAMES = 960  # 20ms at 48kHz


class AudioEngine:
    def __init__(self):
        self._filter = NoiseFilter()
        self._stop_event = threading.Event()
        self._thread = None
        self._input_device = None
        self._intensity = 0.75
        self._last_error = None
        self._prev_default_id: str | None = None

    def get_last_error(self) -> str | None:
        return self._last_error

    def set_input_device(self, device_name: str):
        self._input_device = device_name

    def set_intensity(self, intensity: float):
        self._intensity = max(0.0, min(1.0, intensity))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        if self._prev_default_id is None:
            self._prev_default_id = virtual_device.get_default_capture_id()
        dev_id = virtual_device.find_device_id(virtual_device.MTK_DEVICE_NAME, capture=True)
        if dev_id:
            virtual_device.set_as_default_capture(dev_id)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        if self._prev_default_id:
            virtual_device.set_as_default_capture(self._prev_default_id)
            self._prev_default_id = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        output_device = self._find_cable_input()
        if output_device is None:
            logging.error("AudioEngine: CABLE Input not found")
            self._last_error = "CABLE Input (VB-Cable) não encontrado."
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
                self._last_error = None
                self._stop_event.wait()
        except Exception as e:
            logging.exception("AudioEngine stream error")
            self._last_error = str(e)

    def _callback(self, indata, outdata, frames, time, status):
        chunk = indata[:, 0]
        filtered = self._filter.apply(chunk.copy(), self._intensity)
        outdata[:, 0] = filtered

    def _find_cable_input(self):
        """Return device index for CABLE Input, preferring same host API as input device."""
        all_devices = sd.query_devices()

        # Determine which hostapi the input device uses
        input_hostapi = None
        if self._input_device:
            for d in all_devices:
                if d['name'] == self._input_device:
                    input_hostapi = d['hostapi']
                    break

        # Find CABLE Input in same host API as input — PortAudio requires both in same API
        if input_hostapi is not None:
            for i, d in enumerate(all_devices):
                if ('CABLE Input' in d['name']
                        and d['max_output_channels'] > 0
                        and d['hostapi'] == input_hostapi):
                    return i
            logging.error("AudioEngine: CABLE Input not found in hostapi %d", input_hostapi)
            self._last_error = "CABLE Input (VB-Cable) não encontrado na mesma API de áudio do microfone."
            return None

        # No input device set — pick first CABLE Input found
        for i, d in enumerate(all_devices):
            if 'CABLE Input' in d['name'] and d['max_output_channels'] > 0:
                return i
        return None
