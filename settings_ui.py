import sys
import queue
import threading
import winreg
import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd

from config import Config
from audio_engine import AudioEngine

_APP_NAME = 'MTKNoiseCanceller'


def _query_input_devices() -> list[tuple[int, str]]:
    """Return (index, name) pairs for input devices, preferring MME for compatibility."""
    all_devices = list(enumerate(sd.query_devices()))
    try:
        hostapis = sd.query_hostapis()
        mme_idx = next(i for i, h in enumerate(hostapis) if 'MME' in h['name'])
        devices = [
            (i, d['name']) for i, d in all_devices
            if d['hostapi'] == mme_idx
            and d['max_input_channels'] > 0
            and 'CABLE' not in d['name']
        ]
        if devices:
            return devices
    except Exception:
        pass
    return [
        (i, d['name']) for i, d in all_devices
        if d['max_input_channels'] > 0 and 'CABLE' not in d['name']
    ]
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
_POLL_MS = 100


class SettingsUI:
    def __init__(self, config: Config, engine: AudioEngine, show_on_start: bool = False):
        self._config = config
        self._engine = engine
        self._show_on_start = show_on_start
        self._window = None
        self._cmd_queue = None
        self._pending_update_version: str | None = None
        self._update_version: str | None = None
        self._update_frame = None
        self._update_btn = None
        self._update_label = None

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
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        win.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

        if not self._show_on_start:
            win.withdraw()  # start hidden — shown on demand via request_show()
        self._window = win

        frame = ttk.Frame(win, padding=16)
        frame.grid()

        # Update banner — hidden until a newer version is found
        self._update_frame = ttk.Frame(frame, padding=(0, 0, 0, 4))
        self._update_label = ttk.Label(self._update_frame, text='', foreground='darkgreen')
        self._update_label.grid(row=0, column=0, padx=(0, 8))
        self._update_btn = ttk.Button(
            self._update_frame, text='Atualizar agora', command=self._on_update_click
        )
        self._update_btn.grid(row=0, column=1)
        self._update_frame.grid(row=0, column=0, columnspan=3, sticky='ew')
        self._update_frame.grid_remove()

        # Mic selector
        ttk.Label(frame, text='Microfone:').grid(row=1, column=0, sticky='w', pady=4)
        device_pairs = _query_input_devices()
        self._device_index_map = {name: idx for idx, name in device_pairs}
        device_names = [name for _, name in device_pairs]
        saved_idx = self._config.get('input_device_index')
        saved_name = next((name for idx, name in device_pairs if idx == saved_idx), device_names[0] if device_names else '')
        self._mic_var = tk.StringVar(value=saved_name)
        mic_cb = ttk.Combobox(frame, textvariable=self._mic_var, values=device_names, width=55, state='readonly')
        mic_cb.grid(row=1, column=1, columnspan=2, pady=4, sticky='w')
        mic_cb.bind('<<ComboboxSelected>>', self._on_mic_change)

        # Intensity slider
        ttk.Label(frame, text='Intensidade:').grid(row=2, column=0, sticky='w', pady=4)
        self._intensity_var = tk.DoubleVar(value=self._config.get('intensity', 0.75) * 100)
        slider = ttk.Scale(frame, from_=0, to=100, variable=self._intensity_var, orient='horizontal', length=200)
        slider.grid(row=2, column=1, pady=4)
        slider.bind('<ButtonRelease-1>', self._on_intensity_change)
        self._pct_label = ttk.Label(frame, text=f"{int(self._intensity_var.get())}%", width=5)
        self._pct_label.grid(row=2, column=2, sticky='w')
        self._intensity_var.trace_add('write', self._update_pct_label)

        # Autostart checkbox
        self._autostart_var = tk.BooleanVar(value=self._config.get('autostart', False))
        ttk.Checkbutton(
            frame, text='Iniciar com Windows',
            variable=self._autostart_var, command=self._on_autostart_change,
        ).grid(row=3, column=0, columnspan=3, sticky='w', pady=4)

        # Status label
        self._status_var = tk.StringVar()
        self._refresh_status()
        ttk.Label(frame, textvariable=self._status_var).grid(row=4, column=0, columnspan=3, pady=4)

        # Toggle button
        self._toggle_btn = ttk.Button(frame, command=self._toggle, width=16)
        self._refresh_btn()
        self._toggle_btn.grid(row=5, column=0, columnspan=3, pady=8)

        if self._pending_update_version:
            self._show_update_banner(self._pending_update_version)

    # -- event handlers --

    def _on_mic_change(self, *_):
        name = self._mic_var.get()
        idx = self._device_index_map.get(name)
        self._config.set('input_device_index', idx)
        self._config.set('input_device', name)
        self._config.save()
        if self._engine.is_running():
            self._engine.stop()
        self._engine.set_input_device(idx)
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
        exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
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
            # Give thread time to fail if stream can't open
            self._window.after(800, self._check_engine_started)
        self._config.save()
        self._refresh_status()
        self._refresh_btn()

    def _check_engine_started(self):
        if not self._engine.is_running():
            err = self._engine.get_last_error() or 'Erro desconhecido'
            messagebox.showerror('MTK Noise Canceller', f'Falha ao iniciar áudio:\n{err}')
            self._config.set('active', False)
            self._config.save()
        self._refresh_status()
        self._refresh_btn()

    def _refresh_status(self):
        self._status_var.set('● Ativo' if self._engine.is_running() else '● Inativo')

    def _refresh_btn(self):
        self._toggle_btn.config(text='Desativar' if self._engine.is_running() else 'Ativar')

    def notify_update(self, version: str) -> None:
        self._pending_update_version = version
        if self._window is not None:
            self._window.after(0, lambda v=version: self._show_update_banner(v))

    def _show_update_banner(self, version: str) -> None:
        self._update_version = version
        self._update_label.config(text=f'⬆ v{version} disponível')
        self._update_frame.grid()

    def _on_update_click(self) -> None:
        self._update_btn.config(text='Baixando... 0%', state='disabled')
        threading.Thread(target=self._download_and_install, daemon=True).start()

    def _download_and_install(self) -> None:
        import updater
        try:
            path = updater.download_update(self._update_version, self._on_download_progress)
            updater.launch_installer(path)
            if self._cmd_queue:
                self._cmd_queue.put('quit')
        except Exception as e:
            if self._window is not None:
                self._window.after(0, lambda msg=str(e): self._on_download_error(msg))

    def _on_download_error(self, msg: str) -> None:
        self._update_btn.config(text='Atualizar agora', state='normal')
        messagebox.showerror('MTK Noise Canceller', f'Falha no download:\n{msg}')

    def _on_download_progress(self, pct: int) -> None:
        if self._window is not None:
            self._window.after(0, lambda p=pct: self._update_btn.config(text=f'Baixando... {p}%'))
