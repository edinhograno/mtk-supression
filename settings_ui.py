import sys
import queue
import winreg
import tkinter as tk
from tkinter import ttk
import sounddevice as sd

from config import Config
from audio_engine import AudioEngine

_APP_NAME = 'MTKNoiseCanceller'
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
_POLL_MS = 100


class SettingsUI:
    def __init__(self, config: Config, engine: AudioEngine):
        self._config = config
        self._engine = engine
        self._window = None
        self._cmd_queue = None

    def request_show(self):
        """Thread-safe: enqueue show command."""
        if self._cmd_queue:
            self._cmd_queue.put('show')

    def request_quit(self):
        """Thread-safe: enqueue quit command."""
        if self._cmd_queue:
            self._cmd_queue.put('quit')

    def run_main_loop(self, cmd_queue: queue.Queue):
        """Build window (hidden), poll cmd_queue, run mainloop. CALL FROM MAIN THREAD ONLY."""
        self._cmd_queue = cmd_queue
        self._build()
        self._window.after(_POLL_MS, self._poll)
        self._window.mainloop()

    def _poll(self):
        try:
            while True:
                cmd = self._cmd_queue.get_nowait()
                if cmd == 'show':
                    self._show_window()
                elif cmd == 'quit':
                    self._engine.stop()
                    self._window.destroy()
                    return
        except queue.Empty:
            pass
        self._window.after(_POLL_MS, self._poll)

    def _show_window(self):
        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        self._refresh_status()
        self._refresh_btn()

    def _build(self):
        win = tk.Tk()
        win.title('MTK Noise Canceller')
        win.resizable(False, False)
        win.protocol('WM_DELETE_WINDOW', win.withdraw)
        win.withdraw()  # start hidden — shown on demand via request_show()
        self._window = win

        frame = ttk.Frame(win, padding=16)
        frame.grid()

        # Mic selector
        ttk.Label(frame, text='Microfone:').grid(row=0, column=0, sticky='w', pady=4)
        input_devices = [
            d['name'] for d in sd.query_devices()
            if d['max_input_channels'] > 0 and 'CABLE' not in d['name']
        ]
        saved = self._config.get('input_device') or (input_devices[0] if input_devices else '')
        self._mic_var = tk.StringVar(value=saved)
        mic_cb = ttk.Combobox(frame, textvariable=self._mic_var, values=input_devices, width=32, state='readonly')
        mic_cb.grid(row=0, column=1, columnspan=2, pady=4, sticky='w')
        mic_cb.bind('<<ComboboxSelected>>', self._on_mic_change)

        # Intensity slider
        ttk.Label(frame, text='Intensidade:').grid(row=1, column=0, sticky='w', pady=4)
        self._intensity_var = tk.DoubleVar(value=self._config.get('intensity', 0.75) * 100)
        slider = ttk.Scale(frame, from_=0, to=100, variable=self._intensity_var, orient='horizontal', length=200)
        slider.grid(row=1, column=1, pady=4)
        slider.bind('<ButtonRelease-1>', self._on_intensity_change)
        self._pct_label = ttk.Label(frame, text=f"{int(self._intensity_var.get())}%", width=5)
        self._pct_label.grid(row=1, column=2, sticky='w')
        self._intensity_var.trace_add('write', self._update_pct_label)

        # Autostart checkbox
        self._autostart_var = tk.BooleanVar(value=self._config.get('autostart', False))
        ttk.Checkbutton(
            frame, text='Iniciar com Windows',
            variable=self._autostart_var, command=self._on_autostart_change,
        ).grid(row=2, column=0, columnspan=3, sticky='w', pady=4)

        # Status label
        self._status_var = tk.StringVar()
        self._refresh_status()
        ttk.Label(frame, textvariable=self._status_var).grid(row=3, column=0, columnspan=3, pady=4)

        # Toggle button
        self._toggle_btn = ttk.Button(frame, command=self._toggle, width=16)
        self._refresh_btn()
        self._toggle_btn.grid(row=4, column=0, columnspan=3, pady=8)

    # -- event handlers --

    def _on_mic_change(self, *_):
        name = self._mic_var.get()
        self._config.set('input_device', name)
        self._config.save()
        if self._engine.is_running():
            self._engine.stop()
        self._engine.set_input_device(name)
        if self._config.get('active', True):
            self._engine.start()
        self._refresh_status()
        self._refresh_btn()

    def _on_intensity_change(self, *_):
        val = self._intensity_var.get() / 100.0
        self._config.set('intensity', round(val, 2))
        self._config.save()
        self._engine.set_intensity(val)

    def _update_pct_label(self, *_):
        self._pct_label.config(text=f"{int(self._intensity_var.get())}%")

    def _on_autostart_change(self):
        enable = self._autostart_var.get()
        self._config.set('autostart', enable)
        self._config.save()
        exe = sys.argv[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
            else:
                try:
                    winreg.DeleteValue(k, _APP_NAME)
                except FileNotFoundError:
                    pass

    def _toggle(self):
        if self._engine.is_running():
            self._engine.stop()
            self._config.set('active', False)
        else:
            self._engine.start()
            self._config.set('active', True)
        self._config.save()
        self._refresh_status()
        self._refresh_btn()

    def _refresh_status(self):
        self._status_var.set('● Ativo' if self._engine.is_running() else '● Inativo')

    def _refresh_btn(self):
        self._toggle_btn.config(text='Desativar' if self._engine.is_running() else 'Ativar')
