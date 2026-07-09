import sys
import queue
import threading
import winreg

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QCheckBox,
    QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import sounddevice as sd

from config import Config
from audio_engine import AudioEngine
import style

_APP_NAME = 'MTKNoiseCanceller'
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
_POLL_MS = 100


def _query_input_devices() -> list[tuple[int, str]]:
    """Return (index, name) pairs for input devices, preferring MME."""
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


class _SettingsWindow(QWidget):
    def closeEvent(self, event):
        event.ignore()
        self.hide()


class SettingsUI:
    def __init__(self, config: Config, engine: AudioEngine, show_on_start: bool = False):
        self._config = config
        self._engine = engine
        self._show_on_start = show_on_start
        self._win: QWidget | None = None
        self._cmd_queue: queue.Queue | None = None
        self._pending_update_version: str | None = None
        self._update_version: str | None = None
        self._poll_timer: QTimer | None = None
        self._update_frame: QFrame | None = None
        self._update_btn: QPushButton | None = None
        self._update_label: QLabel | None = None
        self._power_btn: QPushButton | None = None
        self._status_label: QLabel | None = None
        self._pct_label: QLabel | None = None
        self._slider: QSlider | None = None
        self._start_check_timer: QTimer | None = None
        self._dark: bool = False

    def request_show(self):
        """Thread-safe: enqueue show command."""
        if self._cmd_queue:
            self._cmd_queue.put('show')

    def request_quit(self):
        """Thread-safe: enqueue quit command."""
        if self._cmd_queue:
            self._cmd_queue.put('quit')

    def run_main_loop(self, cmd_queue: queue.Queue):
        """Build window, poll cmd_queue, run Qt event loop. CALL FROM MAIN THREAD ONLY."""
        self._cmd_queue = cmd_queue
        app = QApplication.instance() or QApplication(sys.argv)
        self._dark = style.is_dark_mode()
        app.setStyleSheet(style.app_stylesheet(self._dark))
        self._build()
        if self._show_on_start:
            self._win.show()
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(_POLL_MS)
        app.exec()

    def _poll(self):
        try:
            while True:
                cmd = self._cmd_queue.get_nowait()
                if cmd == 'show':
                    self._show_window()
                elif cmd == 'quit':
                    self._engine.stop()
                    app = QApplication.instance()
                    if app:
                        app.quit()
                    return
        except queue.Empty:
            pass

    def _show_window(self):
        self._win.show()
        self._win.raise_()
        self._win.activateWindow()
        self._refresh_status()
        self._refresh_btn()

    def _build(self):
        win = _SettingsWindow()
        win.setWindowTitle('MTK Noise Canceller')
        win.setFixedSize(340, 300)
        self._win = win

        root = QVBoxLayout(win)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(8)

        # ── Update banner (hidden by default) ──
        self._update_frame = QFrame()
        banner_bg = '#1a3024' if self._dark else '#e6f4ea'
        self._update_frame.setStyleSheet(
            f'QFrame {{ background: {banner_bg}; border-radius: 6px; }}'
        )
        banner_row = QHBoxLayout(self._update_frame)
        banner_row.setContentsMargins(8, 6, 8, 6)
        self._update_label = QLabel()
        self._update_label.setStyleSheet(
            f'color: {style.COLOR_ACTIVE}; font-weight: 700; background: transparent;'
        )
        self._update_btn = QPushButton('Atualizar agora')
        self._update_btn.clicked.connect(self._on_update_click)
        banner_row.addWidget(self._update_label)
        banner_row.addStretch()
        banner_row.addWidget(self._update_btn)
        self._update_frame.setVisible(False)
        root.addWidget(self._update_frame)

        # ── Power button ──
        power_col = QVBoxLayout()
        power_col.setAlignment(Qt.AlignCenter)
        self._power_btn = QPushButton('👂')
        self._power_btn.setFixedSize(64, 64)
        self._power_btn.setFont(QFont('Segoe UI', 22))
        self._power_btn.clicked.connect(self._toggle)
        power_col.addWidget(self._power_btn, alignment=Qt.AlignCenter)

        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignCenter)
        lbl_font = QFont('Segoe UI', 11)
        lbl_font.setBold(True)
        self._status_label.setFont(lbl_font)
        power_col.addWidget(self._status_label)
        root.addLayout(power_col)

        # ── Mic card ──
        mic_card = QFrame()
        mic_card.setStyleSheet(
            f'QFrame {{ background: {style.COLOR_CARD}; border-radius: 8px;'
            f' border: 1px solid {style.COLOR_BORDER}; }}'
        )
        mic_col = QVBoxLayout(mic_card)
        mic_col.setContentsMargins(14, 10, 14, 10)
        mic_col.setSpacing(3)
        mic_lbl = QLabel('MICROFONE')
        mic_lbl.setStyleSheet(
            f'color: {style.COLOR_MUTED}; font-size: 10px; font-weight: 600;'
            ' letter-spacing: 0.5px; border: none; background: transparent;'
        )
        mic_col.addWidget(mic_lbl)

        device_pairs = _query_input_devices()
        self._device_index_map = {name: idx for idx, name in device_pairs}
        device_names = [name for _, name in device_pairs]
        saved_idx = self._config.get('input_device_index')
        saved_name = next(
            (name for idx, name in device_pairs if idx == saved_idx),
            device_names[0] if device_names else '',
        )
        self._mic_cb = QComboBox()
        self._mic_cb.addItems(device_names)
        if saved_name in device_names:
            self._mic_cb.setCurrentText(saved_name)
        self._mic_cb.setStyleSheet('border: none; background: transparent;')
        self._mic_cb.currentTextChanged.connect(self._on_mic_change)
        mic_col.addWidget(self._mic_cb)
        root.addWidget(mic_card)

        # ── Intensity card ──
        int_card = QFrame()
        int_card.setStyleSheet(
            f'QFrame {{ background: {style.COLOR_CARD}; border-radius: 8px;'
            f' border: 1px solid {style.COLOR_BORDER}; }}'
        )
        int_col = QVBoxLayout(int_card)
        int_col.setContentsMargins(14, 10, 14, 10)
        int_col.setSpacing(3)

        int_header = QHBoxLayout()
        int_lbl = QLabel('INTENSIDADE')
        int_lbl.setStyleSheet(
            f'color: {style.COLOR_MUTED}; font-size: 10px; font-weight: 600;'
            ' letter-spacing: 0.5px; border: none; background: transparent;'
        )
        self._pct_label = QLabel(f"{int(self._config.get('intensity', 0.75) * 100)}%")
        self._pct_label.setStyleSheet(
            f'color: {style.COLOR_ACCENT}; font-weight: 700;'
            ' border: none; background: transparent;'
        )
        int_header.addWidget(int_lbl)
        int_header.addStretch()
        int_header.addWidget(self._pct_label)
        int_col.addLayout(int_header)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(int(self._config.get('intensity', 0.75) * 100))
        self._slider.setStyleSheet('border: none;')
        self._slider.valueChanged.connect(self._update_pct_label)
        self._slider.sliderReleased.connect(self._on_intensity_change)
        int_col.addWidget(self._slider)
        root.addWidget(int_card)

        # ── Footer ──
        self._autostart_cb = QCheckBox('Iniciar com Windows')
        self._autostart_cb.setChecked(self._config.get('autostart', False))
        self._autostart_cb.toggled.connect(self._on_autostart_change)
        root.addWidget(self._autostart_cb)

        self._refresh_status()
        self._refresh_btn()

        if self._pending_update_version:
            self._show_update_banner(self._pending_update_version)

    # ── Event handlers ──

    def _on_mic_change(self, name: str):
        if self._start_check_timer is not None:
            self._start_check_timer.stop()
            self._start_check_timer = None
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

    def _on_intensity_change(self):
        val = self._slider.value() / 100.0
        self._config.set('intensity', round(val, 2))
        self._config.save()
        self._engine.set_intensity(val)

    def _update_pct_label(self, value: int):
        if self._pct_label:
            self._pct_label.setText(f'{value}%')

    def _on_autostart_change(self, checked: bool):
        self._config.set('autostart', checked)
        self._config.save()
        exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if checked:
                winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
            else:
                try:
                    winreg.DeleteValue(k, _APP_NAME)
                except FileNotFoundError:
                    pass

    def _toggle(self):
        if self._engine.is_running():
            if self._start_check_timer is not None:
                self._start_check_timer.stop()
                self._start_check_timer = None
            self._engine.stop()
            self._config.set('active', False)
            self._config.save()
            self._refresh_status()
            self._refresh_btn()
        else:
            self._engine.start()
            self._config.set('active', True)
            self._config.save()
            self._refresh_status()
            self._refresh_btn()
            self._start_check_timer = QTimer()
            self._start_check_timer.setSingleShot(True)
            self._start_check_timer.timeout.connect(self._check_engine_started)
            self._start_check_timer.start(800)

    def _check_engine_started(self):
        self._start_check_timer = None
        if not self._engine.is_running():
            err = self._engine.get_last_error() or 'Erro desconhecido'
            QMessageBox.critical(
                self._win, 'MTK Noise Canceller', f'Falha ao iniciar áudio:\n{err}'
            )
            self._config.set('active', False)
            self._config.save()
        self._refresh_status()
        self._refresh_btn()

    def _refresh_status(self):
        if not self._status_label:
            return
        active = self._engine.is_running()
        color = style.COLOR_ACTIVE if active else style.COLOR_INACTIVE
        self._status_label.setText('● ATIVO' if active else '● INATIVO')
        self._status_label.setStyleSheet(
            f'color: {color}; font-size: 11px; font-weight: 700;'
        )

    def _refresh_btn(self):
        if not self._power_btn:
            return
        active = self._engine.is_running()
        border = style.COLOR_ACTIVE if active else style.COLOR_INACTIVE
        bg = ('#1a3024' if active else '#3a1a1a') if self._dark else ('#f0fdf4' if active else '#fef2f2')
        self._power_btn.setStyleSheet(
            f'QPushButton {{ border: 3px solid {border}; border-radius: 32px;'
            f' background: {bg}; font-size: 26px; }}'
            f'QPushButton:hover {{ background: {bg}; }}'
        )

    def notify_update(self, version: str) -> None:
        self._pending_update_version = version
        if self._win is not None:
            QTimer.singleShot(0, lambda v=version: self._show_update_banner(v))

    def _show_update_banner(self, version: str) -> None:
        self._update_version = version
        self._update_label.setText(f'⬆ v{version} disponível')
        self._update_frame.setVisible(True)

    def _on_update_click(self) -> None:
        self._update_btn.setText('Baixando... 0%')
        self._update_btn.setEnabled(False)
        threading.Thread(target=self._download_and_install, daemon=True).start()

    def _download_and_install(self) -> None:
        import updater
        try:
            path = updater.download_update(self._update_version, self._on_download_progress)
            updater.launch_installer(path)
            if self._cmd_queue:
                self._cmd_queue.put('quit')
        except Exception as e:
            if self._win is not None:
                QTimer.singleShot(0, lambda msg=str(e): self._on_download_error(msg))

    def _on_download_error(self, msg: str) -> None:
        self._update_btn.setText('Atualizar agora')
        self._update_btn.setEnabled(True)
        QMessageBox.critical(self._win, 'MTK Noise Canceller', f'Falha no download:\n{msg}')

    def _on_download_progress(self, pct: int) -> None:
        if self._win is not None:
            QTimer.singleShot(0, lambda p=pct: self._update_btn.setText(f'Baixando... {p}%'))
