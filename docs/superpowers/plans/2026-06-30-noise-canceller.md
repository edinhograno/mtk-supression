# MTK Noise Canceller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop app that filters microphone noise in real-time and routes clean audio to VB-Cable, distributed as a single `.exe`.

**Architecture:** Entry point (`main.py`) wires together a background audio processing thread (`audio_engine.py` → `noise_filter.py`) with a system tray icon (`tray.py`) and a settings window (`settings_ui.py`). On first run, a wizard (`first_run.py`) installs VB-Cable silently and asks about autostart. Config persists to `~/.mtk-noise-canceller/config.json`.

**Tech Stack:** Python 3.11+, sounddevice, numpy, noisereduce, rnnoise (optional), pystray, Pillow, tkinter (stdlib), PyInstaller

## Global Constraints

- Windows only (uses `winreg`, VB-Cable driver)
- Python 3.11+
- All source files in project root (no `src/` subdirectory)
- Tests in `tests/` directory, mirroring source file names (`test_config.py`, `test_noise_filter.py`, etc.)
- Config stored at `~/.mtk-noise-canceller/config.json`
- VB-Cable installer bundled at `assets/VBCABLE_Setup_x64.exe`
- Sample rate: 48000 Hz, chunk size: 960 frames (20ms)
- `rnnoise` import attempt at `noise_filter.py` init — silent fallback to `noisereduce` on ImportError
- All UI strings in Portuguese (Brazilian)

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `assets/.gitkeep`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: installable Python environment for all subsequent tasks

- [ ] **Step 1: Create requirements.txt**

```
sounddevice==0.4.7
numpy==1.26.4
noisereduce==3.0.3
pystray==0.19.5
Pillow==10.3.0
```

- [ ] **Step 2: Create requirements-dev.txt**

```
-r requirements.txt
pyinstaller==6.6.0
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
*.pyo
.venv/
venv/
dist/
build/
*.spec
!build.spec
*.egg-info/
.pytest_cache/
```

- [ ] **Step 4: Create assets folder and tests package**

```powershell
New-Item -ItemType Directory -Force assets
New-Item -ItemType File -Force assets\.gitkeep
New-Item -ItemType Directory -Force tests
New-Item -ItemType File -Force tests\__init__.py
```

- [ ] **Step 5: Create virtual environment and install deps**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Expected: all packages install without error. `pip show sounddevice` shows version 0.4.7.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore assets/.gitkeep tests/__init__.py
git commit -m "chore: project scaffold with dependencies"
```

---

### Task 2: Config

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` class with `get(key, default)`, `set(key, value)`, `save()`, `reload()`
- Later tasks import: `from config import Config`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_defaults_when_no_file(tmp_path):
    with patch('config.CONFIG_FILE', tmp_path / 'config.json'):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
    assert c.get('first_run') is True
    assert c.get('intensity') == 0.75
    assert c.get('active') is True
    assert c.get('autostart') is False
    assert c.get('input_device') is None


def test_load_existing_file(tmp_path):
    cfg_file = tmp_path / 'config.json'
    cfg_file.write_text(json.dumps({'intensity': 0.5, 'first_run': False}))
    with patch('config.CONFIG_FILE', cfg_file):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
    assert c.get('intensity') == 0.5
    assert c.get('first_run') is False
    assert c.get('active') is True  # default for key not in file


def test_set_and_save(tmp_path):
    cfg_file = tmp_path / 'config.json'
    with patch('config.CONFIG_FILE', cfg_file), patch('config.CONFIG_DIR', tmp_path):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
        c.set('intensity', 0.3)
        c.save()
    data = json.loads(cfg_file.read_text())
    assert data['intensity'] == 0.3


def test_corrupted_file_uses_defaults(tmp_path):
    cfg_file = tmp_path / 'config.json'
    cfg_file.write_text('not json')
    with patch('config.CONFIG_FILE', cfg_file):
        from importlib import reload
        import config as cfg_module
        reload(cfg_module)
        c = cfg_module.Config()
    assert c.get('intensity') == 0.75
```

- [ ] **Step 2: Run to verify failure**

```powershell
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement config.py**

```python
import json
from pathlib import Path

CONFIG_DIR = Path.home() / '.mtk-noise-canceller'
CONFIG_FILE = CONFIG_DIR / 'config.json'

_DEFAULTS = {
    'first_run': True,
    'input_device': None,
    'intensity': 0.75,
    'autostart': False,
    'active': True,
}


class Config:
    def __init__(self):
        self._data = dict(_DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    def reload(self):
        self._data = dict(_DEFAULTS)
        self._load()
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
pytest tests/test_config.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: Config class with load/save and defaults"
```

---

### Task 3: Noise Filter

**Files:**
- Create: `noise_filter.py`
- Create: `tests/test_noise_filter.py`

**Interfaces:**
- Consumes: `numpy` (ndarray chunks), `noisereduce`, optionally `rnnoise`
- Produces: `NoiseFilter` class with `apply(chunk: np.ndarray, intensity: float) -> np.ndarray` and `backend: str` property
- Later tasks import: `from noise_filter import NoiseFilter`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_noise_filter.py
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
```

- [ ] **Step 2: Run to verify failure**

```powershell
pytest tests/test_noise_filter.py -v
```

Expected: `ModuleNotFoundError: No module named 'noise_filter'`

- [ ] **Step 3: Implement noise_filter.py**

```python
import numpy as np

SAMPLE_RATE = 48000

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
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
pytest tests/test_noise_filter.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add noise_filter.py tests/test_noise_filter.py
git commit -m "feat: NoiseFilter with RNNoise/noisereduce hybrid backend"
```

---

### Task 4: Audio Engine

**Files:**
- Create: `audio_engine.py`
- Create: `tests/test_audio_engine.py`

**Interfaces:**
- Consumes: `NoiseFilter` from `noise_filter.py`, `sounddevice`
- Produces: `AudioEngine` class with `start()`, `stop()`, `is_running() -> bool`, `set_input_device(name: str)`, `set_intensity(val: float)`
- Later tasks import: `from audio_engine import AudioEngine`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_audio_engine.py
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
```

- [ ] **Step 2: Run to verify failure**

```powershell
pytest tests/test_audio_engine.py -v
```

Expected: `ModuleNotFoundError: No module named 'audio_engine'`

- [ ] **Step 3: Implement audio_engine.py**

```python
import threading
import numpy as np
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
            pass

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
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
pytest tests/test_audio_engine.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add audio_engine.py tests/test_audio_engine.py
git commit -m "feat: AudioEngine routes mic through noise filter to VB-Cable"
```

---

### Task 5: VB-Cable Setup

**Files:**
- Create: `vbcable_setup.py`
- Create: `tests/test_vbcable_setup.py`

**Interfaces:**
- Consumes: `sounddevice`, `subprocess`, `sys`
- Produces: `is_installed() -> bool`, `get_bundled_installer_path() -> str`, `install(progress_callback=None) -> bool`
- Later tasks import: `from vbcable_setup import is_installed, install`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_vbcable_setup.py
import pytest
from unittest.mock import patch, MagicMock


def _devices_with_cable():
    return [
        {'name': 'CABLE Input (VB-Audio Virtual Cable)', 'max_input_channels': 0, 'max_output_channels': 2},
    ]


def _devices_without_cable():
    return [
        {'name': 'Microfone Realtek', 'max_input_channels': 1, 'max_output_channels': 0},
    ]


def test_is_installed_true_when_cable_present(mocker):
    mocker.patch('sounddevice.query_devices', return_value=_devices_with_cable())
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    assert vbcable_setup.is_installed() is True


def test_is_installed_false_when_cable_absent(mocker):
    mocker.patch('sounddevice.query_devices', return_value=_devices_without_cable())
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    assert vbcable_setup.is_installed() is False


def test_install_returns_true_on_success(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(returncode=0)
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    result = vbcable_setup.install()
    assert result is True
    mock_run.assert_called_once_with([str(installer), '/S'], capture_output=True, timeout=60)


def test_install_returns_false_when_installer_missing(mocker):
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value='C:/nonexistent.exe')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    assert vbcable_setup.install() is False


def test_install_calls_progress_callback(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=0)
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    messages = []
    vbcable_setup.install(progress_callback=messages.append)
    assert len(messages) == 1
    assert 'VB-Cable' in messages[0]
```

- [ ] **Step 2: Run to verify failure**

```powershell
pytest tests/test_vbcable_setup.py -v
```

Expected: `ModuleNotFoundError: No module named 'vbcable_setup'`

- [ ] **Step 3: Implement vbcable_setup.py**

```python
import os
import sys
import subprocess
import sounddevice as sd

INSTALLER_NAME = 'VBCABLE_Setup_x64.exe'


def is_installed() -> bool:
    devices = sd.query_devices()
    return any('CABLE Input' in d['name'] for d in devices)


def get_bundled_installer_path() -> str:
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'assets', INSTALLER_NAME)


def install(progress_callback=None) -> bool:
    installer = get_bundled_installer_path()
    if not os.path.exists(installer):
        return False
    if progress_callback:
        progress_callback('Instalando driver VB-Cable...')
    result = subprocess.run([installer, '/S'], capture_output=True, timeout=60)
    return result.returncode == 0
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
pytest tests/test_vbcable_setup.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Download VB-Cable installer into assets/**

Download `VBCABLE_Driver_Pack43.zip` from https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip, extract, copy `VBCABLE_Setup_x64.exe` to `assets/VBCABLE_Setup_x64.exe`.

Note: this file is a Windows driver installer (~1.5MB). Add to `.gitignore` to avoid committing a binary:

```
assets/VBCABLE_Setup_x64.exe
```

- [ ] **Step 6: Commit**

```bash
git add vbcable_setup.py tests/test_vbcable_setup.py .gitignore
git commit -m "feat: VB-Cable detection and silent install"
```

---

### Task 6: First Run Wizard

**Files:**
- Create: `first_run.py`
- Create: `tests/test_first_run.py`

**Interfaces:**
- Consumes: `Config` from `config.py`, `vbcable_setup.is_installed`, `vbcable_setup.install`, `winreg`
- Produces: `run_if_needed(config: Config) -> bool` (returns False if user cancels, True on success or skip)
- Later tasks import: `from first_run import run_if_needed`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_first_run.py
import pytest
from unittest.mock import patch, MagicMock, call


def make_config(first_run=True, autostart=False):
    c = MagicMock()
    c.get.side_effect = lambda k, default=None: {
        'first_run': first_run,
        'autostart': autostart,
    }.get(k, default)
    return c


def test_skips_when_not_first_run():
    config = make_config(first_run=False)
    from first_run import run_if_needed
    result = run_if_needed(config)
    assert result is True
    config.save.assert_not_called()


def test_returns_false_when_user_declines_vbcable(mocker):
    mocker.patch('vbcable_setup.is_installed', return_value=False)
    mocker.patch('first_run._ask_install_vbcable', return_value=False)
    config = make_config(first_run=True)
    from importlib import reload
    import first_run
    reload(first_run)
    result = first_run.run_if_needed(config)
    assert result is False


def test_returns_true_when_cable_already_installed(mocker):
    mocker.patch('vbcable_setup.is_installed', return_value=True)
    mocker.patch('first_run._ask_autostart', return_value=False)
    mocker.patch('first_run._set_autostart')
    config = make_config(first_run=True)
    from importlib import reload
    import first_run
    reload(first_run)
    result = first_run.run_if_needed(config)
    assert result is True
    config.set.assert_any_call('first_run', False)
    config.save.assert_called_once()


def test_sets_autostart_when_user_says_yes(mocker):
    mocker.patch('vbcable_setup.is_installed', return_value=True)
    mocker.patch('first_run._ask_autostart', return_value=True)
    mock_set_autostart = mocker.patch('first_run._set_autostart')
    config = make_config(first_run=True)
    from importlib import reload
    import first_run
    reload(first_run)
    first_run.run_if_needed(config)
    mock_set_autostart.assert_called_once_with(True)
    config.set.assert_any_call('autostart', True)


def test_returns_false_when_install_fails(mocker):
    mocker.patch('vbcable_setup.is_installed', return_value=False)
    mocker.patch('first_run._ask_install_vbcable', return_value=True)
    mocker.patch('vbcable_setup.install', return_value=False)
    mocker.patch('first_run._show_install_error')
    config = make_config(first_run=True)
    from importlib import reload
    import first_run
    reload(first_run)
    result = first_run.run_if_needed(config)
    assert result is False
```

- [ ] **Step 2: Run to verify failure**

```powershell
pytest tests/test_first_run.py -v
```

Expected: `ModuleNotFoundError: No module named 'first_run'`

- [ ] **Step 3: Implement first_run.py**

```python
import sys
import winreg
import tkinter as tk
from tkinter import messagebox

import vbcable_setup
from config import Config

_APP_NAME = 'MTKNoiseCanceller'
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


def run_if_needed(config: Config) -> bool:
    if not config.get('first_run', True):
        return True

    if not vbcable_setup.is_installed():
        if not _ask_install_vbcable():
            return False
        if not vbcable_setup.install():
            _show_install_error()
            return False

    autostart = _ask_autostart()
    config.set('autostart', autostart)
    _set_autostart(autostart)
    config.set('first_run', False)
    config.save()
    return True


def _ask_install_vbcable() -> bool:
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        'MTK Noise Canceller',
        'Este app precisa instalar um driver de áudio virtual (VB-Cable) para funcionar.\n\n'
        'Deseja instalar agora?',
    )
    root.destroy()
    return result


def _ask_autostart() -> bool:
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        'MTK Noise Canceller',
        'Deseja que o app inicie automaticamente com o Windows?',
    )
    root.destroy()
    return result


def _show_install_error():
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        'MTK Noise Canceller',
        'Falha ao instalar VB-Cable.\nTente executar o app como administrador.',
    )
    root.destroy()


def _set_autostart(enable: bool):
    exe = sys.argv[0]
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
pytest tests/test_first_run.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add first_run.py tests/test_first_run.py
git commit -m "feat: first-run wizard for VB-Cable install and autostart"
```

---

### Task 7: Tray Icon

**Files:**
- Create: `tray.py`

**Interfaces:**
- Consumes: `AudioEngine` from `audio_engine.py`, `Config` from `config.py`, `pystray`, `Pillow`
- Produces: `TrayApp` class with `run_in_thread()` (non-blocking, starts daemon thread), `update_icon()`
- Later tasks import: `from tray import TrayApp`

**Threading note:** `pystray.Icon.run()` blocks its thread. `tkinter` must run on the main thread. Solution: tray runs in a daemon thread; main thread owns the tkinter loop. `on_settings` and `on_quit` are called from the tray thread via a `queue.Queue` — the tkinter loop polls the queue with `after()`.

No unit tests — `pystray` spawns native OS icon loop that cannot be driven in CI. Manual test in Task 9.

- [ ] **Step 1: Implement tray.py**

```python
import threading
import pystray
from PIL import Image, ImageDraw

from config import Config
from audio_engine import AudioEngine


def _make_icon(active: bool) -> Image.Image:
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (0, 180, 0, 255) if active else (180, 0, 0, 255)
    draw.ellipse([8, 8, 56, 56], fill=color)
    return img


class TrayApp:
    def __init__(self, config: Config, engine: AudioEngine, on_settings, on_quit):
        self._config = config
        self._engine = engine
        self._on_settings = on_settings  # callable, called from tray thread
        self._on_quit = on_quit          # callable, called from tray thread
        self._icon = None

    def run_in_thread(self):
        """Start tray icon in a daemon thread. Returns immediately."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def update_icon(self):
        if self._icon:
            self._icon.icon = _make_icon(self._engine.is_running())

    def _run(self):
        self._icon = pystray.Icon(
            'MTKNoiseCanceller',
            _make_icon(self._engine.is_running()),
            'MTK Noise Canceller',
            menu=pystray.Menu(
                pystray.MenuItem('Configurações', self._open_settings),
                pystray.MenuItem('Ativar/Desativar', self._toggle),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Sair', self._quit),
            ),
        )
        self._icon.run()

    def _toggle(self):
        if self._engine.is_running():
            self._engine.stop()
            self._config.set('active', False)
        else:
            self._engine.start()
            self._config.set('active', True)
        self._config.save()
        self.update_icon()

    def _open_settings(self):
        self._on_settings()

    def _quit(self):
        self._engine.stop()
        if self._icon:
            self._icon.stop()
        self._on_quit()
```

- [ ] **Step 2: Commit**

```bash
git add tray.py
git commit -m "feat: system tray icon runs in daemon thread"
```

---

### Task 8: Settings Window

**Files:**
- Create: `settings_ui.py`

**Interfaces:**
- Consumes: `AudioEngine`, `Config`, `sounddevice`, `winreg`, `tkinter`, `queue.Queue`
- Produces: `SettingsUI` class with:
  - `run_main_loop(cmd_queue: queue.Queue)` — builds hidden window, starts polling queue, calls `mainloop()`. Blocks. Call from main thread.
  - `request_show()` — enqueues `'show'` command (safe to call from any thread)
  - `request_quit()` — enqueues `'quit'` command
- Later tasks import: `from settings_ui import SettingsUI`

**Threading note:** `run_main_loop()` must be called from the main thread. `pystray` callbacks (from tray thread) call `request_show()` / `request_quit()` which are thread-safe queue puts. The tkinter `after()` loop polls the queue every 100ms.

No unit tests — `tkinter` mainloop cannot run headless in CI. Manual test in Task 9.

- [ ] **Step 1: Implement settings_ui.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add settings_ui.py
git commit -m "feat: settings window with queue-based thread-safe show/quit"
```

---

### Task 9: Main Entry Point + Manual Integration Test

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: all modules above, `queue`
- Produces: runnable app

**Threading layout:**
- Main thread: tkinter `run_main_loop()` (blocks until quit)
- Daemon thread: pystray tray icon (`TrayApp.run_in_thread()`)
- Daemon thread: audio engine (`AudioEngine.start()`)
- `cmd_queue`: bridge between tray thread and main thread

- [ ] **Step 1: Implement main.py**

```python
import sys
import queue
from config import Config
from audio_engine import AudioEngine
from first_run import run_if_needed
from settings_ui import SettingsUI
from tray import TrayApp


def main():
    config = Config()
    engine = AudioEngine()

    if not run_if_needed(config):
        sys.exit(0)

    device = config.get('input_device')
    if device:
        engine.set_input_device(device)
    engine.set_intensity(config.get('intensity', 0.75))

    if config.get('active', True):
        engine.start()

    cmd_queue = queue.Queue()
    ui = SettingsUI(config, engine)

    tray = TrayApp(
        config=config,
        engine=engine,
        on_settings=ui.request_show,
        on_quit=ui.request_quit,
    )
    tray.run_in_thread()

    # Blocks on main thread until quit command received
    ui.run_main_loop(cmd_queue)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run full test suite**

```powershell
pytest tests/ -v
```

Expected: all unit tests pass (config, noise_filter, audio_engine, vbcable_setup, first_run).

- [ ] **Step 3: Manual integration test**

```powershell
python main.py
```

Verify:
- First run: dialog asks to install VB-Cable (click Yes if not installed, or skip if already installed)
- Dialog asks about autostart
- Tray icon appears (green circle)
- Right-click → Configurações opens settings window
- Mic dropdown lists input devices
- Intensity slider changes value and label
- "Desativar" button stops engine (icon turns red)
- "Ativar" button restarts engine (icon turns green)
- In Meet/Teams/Discord: select "CABLE Output (VB-Audio)" as microphone — voice should come through with noise removed

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: main entry point wiring tray, settings, and audio engine"
```

---

### Task 10: PyInstaller Packaging

**Files:**
- Create: `build.spec`

**Interfaces:**
- Consumes: all source files, `assets/VBCABLE_Setup_x64.exe`, `assets/icon.ico`
- Produces: `dist/mtk-noise-canceller.exe`

**Pre-requisite:** Create a 64x64 `assets/icon.ico`. Quickest option:

```python
# run once to generate icon
from PIL import Image, ImageDraw
img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([4, 4, 60, 60], fill=(0, 160, 0, 255))
img.save('assets/icon.ico')
```

- [ ] **Step 1: Generate icon**

```powershell
python -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (64, 64), (0,0,0,0))
draw = ImageDraw.Draw(img)
draw.ellipse([4,4,60,60], fill=(0,160,0,255))
img.save('assets/icon.ico')
"
```

- [ ] **Step 2: Create build.spec**

```python
# build.spec
import os
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/VBCABLE_Setup_x64.exe', 'assets'),
        ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=[
        'sounddevice',
        'noisereduce',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mtk-noise-canceller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icon.ico',
)
```

- [ ] **Step 3: Build**

```powershell
pyinstaller build.spec
```

Expected: `dist/mtk-noise-canceller.exe` created (~30–60MB). No errors in output.

- [ ] **Step 4: Test the .exe**

```powershell
.\dist\mtk-noise-canceller.exe
```

Verify same behavior as `python main.py` from Task 9, Step 3.

- [ ] **Step 5: Commit**

```bash
git add build.spec assets/icon.ico
git commit -m "chore: PyInstaller build spec for single-file exe distribution"
```

---

## Running All Tests

```powershell
pytest tests/ -v --tb=short
```

Expected: 22 tests, all passing.
