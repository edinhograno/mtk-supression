# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir a UI tkinter por PySide6 moderna com identidade visual, mantendo toda a lógica de negócio intacta.

**Architecture:** Novo `style.py` centraliza cores e QSS. `settings_ui.py` e `first_run.py` são reescritos em PySide6 mantendo as mesmas interfaces públicas. `tray.py` ganha ícone de orelha desenhado com PIL. `build.spec` adiciona PySide6 e remove tkinter.

**Tech Stack:** Python 3.14, PySide6 6.x, PIL/Pillow (já presente), pystray (mantido), PyInstaller onefile.

## Global Constraints

- Python 3.14, Windows 10/11 64-bit
- `PySide6>=6.6` adicionado ao `requirements.txt`
- `style.py` exporta: `COLOR_ACCENT='#0078D4'`, `COLOR_ACTIVE='#1a7a36'`, `COLOR_INACTIVE='#c0392b'`, `COLOR_BG='#ffffff'`, `COLOR_CARD='#f8f9fa'`, `COLOR_BORDER='#eeeeee'`, `COLOR_TEXT='#222222'`, `COLOR_MUTED='#999999'`, `app_stylesheet() -> str`
- Interface pública de `SettingsUI` não muda: `__init__(config, engine, show_on_start=False)`, `run_main_loop(cmd_queue)`, `request_show()`, `request_quit()`, `notify_update(version)`
- Interface pública de `TrayApp` não muda: `__init__`, `run_in_thread()`, `update_icon()`
- Interface pública de `first_run.py` não muda: `run_if_needed(config) -> bool`; helpers internos `_ask_install_vbcable`, `_install_with_progress`, `_ask_autostart`, `_show_install_error`, `_set_autostart` mantidos como funções de módulo (os testes existentes as patcham)
- Fechar janela de configurações → `hide()`, não encerra o app
- Thread-safety: toda atualização de UI de threads externas via `QTimer.singleShot(0, fn)`
- Sem testes unitários para UI (Qt mainloop incompatível com pytest headless); testes de `style.py` e `tray._make_icon` são permitidos (sem Qt)
- `QApplication` singleton: `QApplication.instance() or QApplication(sys.argv)` em `run_main_loop` e `run_if_needed`
- Sem alteração em `main.py`, `config.py`, `audio_engine.py`, `vbcable_setup.py`, `noise_filter.py`, `updater.py`, `virtual_device.py`

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `style.py` | Criar | Constantes de cor + QSS stylesheet |
| `requirements.txt` | Modificar | Adicionar `PySide6>=6.6` |
| `tests/test_style.py` | Criar | Testes de constantes e stylesheet |
| `settings_ui.py` | Reescrever | Janela de configurações PySide6 |
| `first_run.py` | Reescrever | Wizard de primeira execução PySide6 |
| `tray.py` | Modificar | `_make_icon` → orelha com PIL |
| `build.spec` | Modificar | PySide6 + remover tkinter |
| `tests/test_tray.py` | Criar | Testes de `_make_icon` |

---

## Task 1: style.py + requirements.txt + tests

**Files:**
- Create: `style.py`
- Modify: `requirements.txt`
- Create: `tests/test_style.py`

**Interfaces:**
- Produces:
  - `COLOR_ACCENT: str = '#0078D4'`
  - `COLOR_ACTIVE: str = '#1a7a36'`
  - `COLOR_INACTIVE: str = '#c0392b'`
  - `COLOR_BG: str = '#ffffff'`
  - `COLOR_CARD: str = '#f8f9fa'`
  - `COLOR_BORDER: str = '#eeeeee'`
  - `COLOR_TEXT: str = '#222222'`
  - `COLOR_MUTED: str = '#999999'`
  - `app_stylesheet() -> str`

- [ ] **Step 1: Escrever tests/test_style.py**

```python
def test_color_constants_are_hex_strings():
    import style
    names = (
        'COLOR_ACCENT', 'COLOR_ACTIVE', 'COLOR_INACTIVE', 'COLOR_BG',
        'COLOR_CARD', 'COLOR_BORDER', 'COLOR_TEXT', 'COLOR_MUTED',
    )
    for name in names:
        val = getattr(style, name)
        assert isinstance(val, str), f'{name} deve ser str'
        assert val.startswith('#'), f'{name} deve começar com #'
        assert len(val) == 7, f'{name} deve ter 7 chars (#rrggbb)'


def test_color_values_match_spec():
    import style
    assert style.COLOR_ACCENT   == '#0078D4'
    assert style.COLOR_ACTIVE   == '#1a7a36'
    assert style.COLOR_INACTIVE == '#c0392b'
    assert style.COLOR_BG       == '#ffffff'
    assert style.COLOR_CARD     == '#f8f9fa'
    assert style.COLOR_BORDER   == '#eeeeee'
    assert style.COLOR_TEXT     == '#222222'
    assert style.COLOR_MUTED    == '#999999'


def test_app_stylesheet_returns_nonempty_string():
    import style
    sheet = style.app_stylesheet()
    assert isinstance(sheet, str)
    assert len(sheet) > 100


def test_app_stylesheet_contains_required_selectors():
    import style
    sheet = style.app_stylesheet()
    for selector in ('QWidget', 'QComboBox', 'QSlider', 'QCheckBox'):
        assert selector in sheet, f'stylesheet deve conter {selector}'
```

- [ ] **Step 2: Rodar — esperar falha**

```
cd c:\Git\mtk-noise-canceller
.venv\Scripts\python -m pytest tests/test_style.py -v
```

Expected: `ModuleNotFoundError: No module named 'style'`

- [ ] **Step 3: Adicionar PySide6 ao requirements.txt**

Abrir `requirements.txt` e adicionar no final:
```
PySide6>=6.6
```

Instalar no venv:
```
.venv\Scripts\pip install "PySide6>=6.6"
```

- [ ] **Step 4: Criar style.py**

```python
COLOR_ACCENT   = '#0078D4'
COLOR_ACTIVE   = '#1a7a36'
COLOR_INACTIVE = '#c0392b'
COLOR_BG       = '#ffffff'
COLOR_CARD     = '#f8f9fa'
COLOR_BORDER   = '#eeeeee'
COLOR_TEXT     = '#222222'
COLOR_MUTED    = '#999999'


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 12px;
        color: {COLOR_TEXT};
        background-color: {COLOR_BG};
    }}
    QComboBox {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        background: {COLOR_CARD};
    }}
    QComboBox:focus {{ border-color: {COLOR_ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: #e0e0e0;
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {COLOR_ACCENT};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 14px; height: 14px;
        background: {COLOR_ACCENT};
        border-radius: 7px;
        margin: -5px 0;
    }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 4px;
        border: 2px solid {COLOR_ACCENT};
        background: white;
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 5px 14px;
        background: {COLOR_CARD};
        color: {COLOR_TEXT};
    }}
    QPushButton:hover {{ background: #eeeeee; }}
    QPushButton:pressed {{ background: #e0e0e0; }}
    """
```

- [ ] **Step 5: Rodar — esperar todos passarem**

```
.venv\Scripts\python -m pytest tests/test_style.py -v
```

Expected:
```
PASSED tests/test_style.py::test_color_constants_are_hex_strings
PASSED tests/test_style.py::test_color_values_match_spec
PASSED tests/test_style.py::test_app_stylesheet_returns_nonempty_string
PASSED tests/test_style.py::test_app_stylesheet_contains_required_selectors
4 passed
```

- [ ] **Step 6: Commit**

```bash
git add style.py requirements.txt tests/test_style.py
git commit -m "feat: add style.py with PySide6 color tokens and QSS stylesheet"
```

---

## Task 2: Rewrite settings_ui.py

**Files:**
- Modify: `settings_ui.py` (rewrite completo)

**Interfaces:**
- Consumes de Task 1: `style.COLOR_ACTIVE`, `style.COLOR_INACTIVE`, `style.COLOR_ACCENT`, `style.COLOR_CARD`, `style.COLOR_BORDER`, `style.COLOR_MUTED`, `style.app_stylesheet()`
- Preserva (main.py depende):
  - `SettingsUI.__init__(config: Config, engine: AudioEngine, show_on_start: bool = False)`
  - `SettingsUI.run_main_loop(cmd_queue: queue.Queue)` — cria QApplication, constrói janela, inicia QTimer 100ms, chama `app.exec()` (bloqueante)
  - `SettingsUI.request_show()` — enfileira 'show' no cmd_queue
  - `SettingsUI.request_quit()` — enfileira 'quit' no cmd_queue
  - `SettingsUI.notify_update(version: str) -> None` — thread-safe via QTimer.singleShot

- [ ] **Step 1: Rodar suite existente como baseline**

```
.venv\Scripts\python -m pytest tests/ -v --ignore=tests/test_style.py
```

Expected: todos os testes existentes passam (exceto possíveis falhas de ambiente já conhecidas).

- [ ] **Step 2: Reescrever settings_ui.py**

Substituir o conteúdo inteiro de `settings_ui.py`:

```python
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
        app.setStyleSheet(style.app_stylesheet())
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
        win = QWidget()
        win.setWindowTitle('MTK Noise Canceller')
        win.setFixedSize(340, 300)
        win.closeEvent = lambda e: (e.ignore(), win.hide())
        self._win = win

        root = QVBoxLayout(win)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(8)

        # ── Update banner (hidden by default) ──
        self._update_frame = QFrame()
        self._update_frame.setStyleSheet(
            'QFrame { background: #e6f4ea; border-radius: 6px; }'
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
            QTimer.singleShot(800, self._check_engine_started)

    def _check_engine_started(self):
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
        bg = '#f0fdf4' if active else '#fef2f2'
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
```

- [ ] **Step 3: Verificar que testes não-UI ainda passam**

```
.venv\Scripts\python -m pytest tests/ -v --ignore=tests/test_style.py
```

Expected: mesmos resultados de antes (não-UI tests passam; settings_ui não tem testes).

- [ ] **Step 4: Teste manual — abrir a janela**

```
.venv\Scripts\python -c "
import queue
from config import Config
from audio_engine import AudioEngine
from settings_ui import SettingsUI
config = Config()
engine = AudioEngine()
ui = SettingsUI(config, engine, show_on_start=True)
ui.run_main_loop(queue.Queue())
"
```

Verificar: janela aparece com power button (👂), status label, mic card, intensity card, checkbox. Fechar com X → janela some mas processo não encerra (Ctrl+C para parar).

- [ ] **Step 5: Commit**

```bash
git add settings_ui.py
git commit -m "feat: rewrite settings_ui with PySide6 — power button, mic/intensity cards"
```

---

## Task 3: Rewrite first_run.py

**Files:**
- Modify: `first_run.py` (rewrite completo)

**Interfaces:**
- Consumes de Task 1: `style.app_stylesheet()`
- Preserva (main.py e tests/test_first_run.py dependem):
  - `run_if_needed(config: Config) -> bool`
  - `_ask_install_vbcable() -> bool` — função de módulo, patcheável
  - `_install_with_progress() -> bool` — função de módulo, patcheável
  - `_ask_autostart() -> bool` — função de módulo, patcheável
  - `_show_install_error()` — função de módulo, patcheável
  - `_set_autostart(enable: bool)` — função de módulo, patcheável

- [ ] **Step 1: Rodar test_first_run.py como baseline**

```
.venv\Scripts\python -m pytest tests/test_first_run.py -v
```

Expected: 5 testes passam.

- [ ] **Step 2: Reescrever first_run.py**

Substituir o conteúdo inteiro de `first_run.py`:

```python
import sys
import threading
import winreg

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar,
)
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QFont

import vbcable_setup
from config import Config
import style

_APP_NAME = 'MTKNoiseCanceller'
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


class _InstallSignals(QObject):
    progress = Signal(str)
    done = Signal(bool)


def run_if_needed(config: Config) -> bool:
    if not config.get('first_run', True):
        return True

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(style.app_stylesheet())

    if not vbcable_setup.is_installed():
        if not _ask_install_vbcable():
            return False
        ok = _install_with_progress()
        if not ok:
            _show_install_error()
            return False

    autostart = _ask_autostart()
    config.set('autostart', autostart)
    _set_autostart(autostart)
    config.set('first_run', False)
    config.save()
    return True


def _ask_install_vbcable() -> bool:
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 260)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(16)

    ear = QLabel('👂')
    ear.setFont(QFont('Segoe UI', 48))
    ear.setAlignment(Qt.AlignCenter)
    layout.addWidget(ear)

    title = QLabel('MTK Noise Canceller')
    f = QFont('Segoe UI', 14)
    f.setBold(True)
    title.setFont(f)
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)

    body = QLabel(
        'Bem-vindo! Precisamos instalar o VB-Cable para processar o áudio.\n\n'
        'O driver será baixado e instalado automaticamente (~5 MB).'
    )
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignCenter)
    layout.addWidget(body)

    btns = QHBoxLayout()
    cancel = QPushButton('Cancelar')
    ok_btn = QPushButton('Continuar')
    ok_btn.setDefault(True)
    btns.addWidget(cancel)
    btns.addWidget(ok_btn)
    layout.addLayout(btns)

    result = [False]
    cancel.clicked.connect(dlg.reject)
    ok_btn.clicked.connect(lambda: (result.__setitem__(0, True), dlg.accept()))
    dlg.exec()
    return result[0]


def _install_with_progress() -> bool:
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 160)
    dlg.setModal(True)
    dlg.closeEvent = lambda e: e.ignore()

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(12)

    status_lbl = QLabel('Iniciando...')
    status_lbl.setAlignment(Qt.AlignCenter)
    layout.addWidget(status_lbl)

    bar = QProgressBar()
    bar.setRange(0, 0)
    layout.addWidget(bar)

    result = [False]
    sig = _InstallSignals()
    sig.progress.connect(status_lbl.setText)
    sig.done.connect(lambda ok: (result.__setitem__(0, ok), dlg.accept()))

    def worker():
        ok = vbcable_setup.install(progress_callback=sig.progress.emit)
        sig.done.emit(ok)

    threading.Thread(target=worker, daemon=True).start()
    dlg.exec()
    return result[0]


def _ask_autostart() -> bool:
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 180)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(16)

    body = QLabel(
        'Deseja que o MTK Noise Canceller\ninicialize automaticamente com o Windows?'
    )
    body.setAlignment(Qt.AlignCenter)
    body.setWordWrap(True)
    layout.addWidget(body)

    btns = QHBoxLayout()
    no_btn = QPushButton('Não')
    yes_btn = QPushButton('Sim')
    yes_btn.setDefault(True)
    btns.addWidget(no_btn)
    btns.addWidget(yes_btn)
    layout.addLayout(btns)

    result = [False]
    no_btn.clicked.connect(dlg.reject)
    yes_btn.clicked.connect(lambda: (result.__setitem__(0, True), dlg.accept()))
    dlg.exec()
    return result[0]


def _show_install_error():
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 180)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(16)

    body = QLabel(
        'Falha ao instalar VB-Cable.\n\n'
        'Verifique sua conexão com a internet e tente novamente.\n'
        'Se o problema persistir, execute o app como administrador.'
    )
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignCenter)
    layout.addWidget(body)

    close_btn = QPushButton('Fechar')
    close_btn.clicked.connect(dlg.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    dlg.exec()


def _set_autostart(enable: bool):
    exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
```

- [ ] **Step 3: Rodar test_first_run.py — esperar 5 testes passarem**

```
.venv\Scripts\python -m pytest tests/test_first_run.py -v
```

Expected: 5 passed. Os testes existentes patcham as funções internas (`_ask_install_vbcable`, `_ask_autostart`, `_set_autostart`), por isso não criam dialogs Qt e continuam headless-safe.

- [ ] **Step 4: Teste manual — wizard de primeira execução**

Resetar config para simular primeiro uso:

```
.venv\Scripts\python -c "
from config import Config
c = Config()
c.set('first_run', True)
c.save()
"
```

Depois executar:

```
.venv\Scripts\python main.py
```

Verificar: tela 1 (Bem-vindo + ícone 👂 + botão Continuar), tela 2 (progress bar + download/install), tela 3 (autostart), janela principal abre após wizard.

- [ ] **Step 5: Commit**

```bash
git add first_run.py
git commit -m "feat: rewrite first_run with PySide6 wizard — 3 dialogs, progress bar"
```

---

## Task 4: tray.py ear icon + build.spec + tests

**Files:**
- Modify: `tray.py` (somente função `_make_icon`)
- Modify: `build.spec`
- Create: `tests/test_tray.py`

**Interfaces:**
- Preserva:
  - `_make_icon(active: bool) -> PIL.Image.Image` — retorna RGBA 64×64
  - Toda interface pública de `TrayApp` inalterada

- [ ] **Step 1: Criar tests/test_tray.py**

```python
def test_make_icon_returns_rgba_64x64_when_active():
    from tray import _make_icon
    img = _make_icon(True)
    assert img.size == (64, 64)
    assert img.mode == 'RGBA'


def test_make_icon_returns_rgba_64x64_when_inactive():
    from tray import _make_icon
    img = _make_icon(False)
    assert img.size == (64, 64)
    assert img.mode == 'RGBA'


def test_make_icon_active_has_green_pixels():
    from tray import _make_icon
    img = _make_icon(True)
    pixels = list(img.getdata())
    # Active icon: at least some visible green-dominant pixels
    visible = [p for p in pixels if p[3] > 128]
    green = [p for p in visible if p[1] > p[0] and p[1] > p[2]]
    assert len(green) > 5, 'active icon deve ter pixels verdes visíveis'


def test_make_icon_inactive_has_red_pixels():
    from tray import _make_icon
    img = _make_icon(False)
    pixels = list(img.getdata())
    visible = [p for p in pixels if p[3] > 128]
    red = [p for p in visible if p[0] > p[1] and p[0] > p[2]]
    assert len(red) > 5, 'inactive icon deve ter pixels vermelhos visíveis'
```

- [ ] **Step 2: Rodar — esperar falha**

```
.venv\Scripts\python -m pytest tests/test_tray.py -v
```

Expected: 2 primeiros passam (size/mode não mudam), 2 últimos falham (cores erradas — círculo atual não é verde/vermelho dominante como esperado). Ou todos passam se o círculo atual já usa RGB puros. Verificar output.

- [ ] **Step 3: Substituir _make_icon em tray.py**

Localizar e substituir apenas a função `_make_icon` (mantendo todo o resto do arquivo):

```python
def _make_icon(active: bool) -> Image.Image:
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = (26, 122, 54, 255) if active else (192, 57, 43, 255)
    w = 4

    # Outer ear rim — open arc (C-shape, opening on the left)
    draw.arc([14, 8, 50, 52], start=210, end=330, fill=c, width=w)
    # Left side vertical connector (closes the C)
    draw.line([(15, 28), (15, 38)], fill=c, width=w)
    # Earlobe — small filled ellipse at bottom
    draw.ellipse([24, 48, 40, 60], fill=c)

    # Inner helix — smaller concentric arc
    draw.arc([22, 16, 42, 38], start=210, end=350, fill=c, width=3)

    # Ear canal — small filled dot
    draw.ellipse([28, 30, 36, 38], fill=c)

    if not active:
        # Diagonal slash overlay
        draw.line([(12, 12), (52, 52)], fill=(192, 57, 43, 178), width=w)

    return img
```

- [ ] **Step 4: Rodar — esperar 4 testes passarem**

```
.venv\Scripts\python -m pytest tests/test_tray.py -v
```

Expected:
```
PASSED tests/test_tray.py::test_make_icon_returns_rgba_64x64_when_active
PASSED tests/test_tray.py::test_make_icon_returns_rgba_64x64_when_inactive
PASSED tests/test_tray.py::test_make_icon_active_has_green_pixels
PASSED tests/test_tray.py::test_make_icon_inactive_has_red_pixels
4 passed
```

- [ ] **Step 5: Rodar suite completa**

```
.venv\Scripts\python -m pytest tests/ -v
```

Expected: todos os testes passam (style × 4, tray × 4, virtual_device × 11, vbcable_setup × 7, audio_engine × 10, first_run × 5, config × 4, updater × 9, version × 2, noise_filter × some = total ≥ 50).

- [ ] **Step 6: Atualizar build.spec**

Abrir `build.spec`. Adicionar no topo (após os imports existentes):

```python
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

pyside6_datas = collect_data_files('PySide6')
pyside6_binaries = collect_dynamic_libs('PySide6')
```

Substituir a lista `binaries` na Analysis:

```python
    binaries=[*pedalboard_binaries, *sounddevice_binaries, *pyside6_binaries],
```

Substituir a lista `datas` na Analysis:

```python
    datas=[
        ('assets/icon.ico', 'assets'),
        *pedalboard_datas,
        *sounddevice_datas,
        *pyside6_datas,
    ],
```

Substituir `hiddenimports` na Analysis (remover tkinter, adicionar PySide6):

```python
    hiddenimports=[
        'comtypes',
        'comtypes.client',
        'pedalboard',
        'pedalboard.pedalboard',
        'pedalboard._pedalboard',
        'pedalboard.io',
        'sounddevice',
        'numpy',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.IcoImagePlugin',
        'queue',
        'PySide6',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
    ],
```

Substituir `excludes`:

```python
    excludes=['noisereduce', 'librosa', 'scipy', 'matplotlib', 'tkinter'],
```

- [ ] **Step 7: Commit**

```bash
git add tray.py build.spec tests/test_tray.py
git commit -m "feat: ear icon in tray, PySide6 in build.spec, remove tkinter"
```

---

## Teste Manual Final (após todos os tasks)

```
.venv\Scripts\python main.py
```

Verificar:
1. Se `first_run=true` no config: wizard abre (tela Bem-vindo → Instalando → Autostart)
2. Janela principal: power button 👂, status "● ATIVO" (verde) ou "● INATIVO" (vermelho)
3. Borda do botão muda de cor ao ligar/desligar
4. Slider de intensidade atualiza `%` em tempo real
5. Fechar janela com X → some para bandeja (não encerra)
6. Ícone de bandeja: orelha verde (ativo) / vermelha com slash (inativo)
7. Menu da bandeja: Configurações, Ativar/Desativar, Sair
