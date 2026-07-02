# Inno Setup Installer + Auto-Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a proper Windows installer (Inno Setup) and an in-app auto-update system that checks GitHub Releases and downloads new versions via a banner in the Settings window.

**Architecture:** `version.py` is the single source of truth for the version string. `updater.py` (stdlib only) checks the GitHub Releases API, downloads the new setup.exe to `%TEMP%`, and launches it. `settings_ui.py` gains a hidden banner frame that appears when an update is found, with a download-and-install button. Inno Setup produces `mtk-noise-canceller-setup.exe` which installs the app to Program Files and creates Start Menu shortcuts; VB-Cable is left to `first_run.py` (already uses PowerShell `Start-Process -Verb RunAs` for UAC — no need for `uac_admin=True` on the app exe).

**Tech Stack:** Python 3.14, PyInstaller 6.x, tkinter, urllib (stdlib), Inno Setup 6, pystray

## Global Constraints

- Python 3.14, Windows 10/11 64-bit only
- No new PyPI dependencies — `updater.py` uses stdlib only
- Inno Setup 6 must be installed at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` on dev machine (not in repo)
- GitHub repo: `edinhograno/mtk-supression` (public)
- Asset filename published to GitHub Releases: `mtk-noise-canceller-setup.exe`
- All existing tests must continue passing throughout
- Version format: `MAJOR.MINOR.PATCH` (e.g., `1.0.0`) — no `v` prefix in `__version__`
- `uac_admin` removed from `build.spec` — VB-Cable UAC handled by `vbcable_setup.py` subprocess

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `version.py` | Create | `__version__` string — single source of truth |
| `updater.py` | Create | GitHub API check, download, launcher |
| `tests/test_version.py` | Create | Format validation |
| `tests/test_updater.py` | Create | Mock-based unit tests for all updater functions |
| `installer/mtk.iss` | Create | Inno Setup script |
| `settings_ui.py` | Modify | Hidden update banner + download/install flow |
| `main.py` | Modify | Background update check thread (startup + daily) |
| `build.spec` | Modify | Remove `uac_admin=True` |
| `build.ps1` | Modify | Inject version into `.iss`, call ISCC after PyInstaller |
| `release.ps1` | Modify | Upload `setup.exe` instead of bare exe |

---

### Task 1: version.py

**Files:**
- Create: `version.py`
- Create: `tests/test_version.py`

**Interfaces:**
- Produces: `__version__: str` — imported by `updater.py`; read by `build.ps1` to inject into `.iss`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_version.py
def test_version_format():
    from version import __version__
    parts = __version__.split('.')
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)

def test_version_is_string():
    from version import __version__
    assert isinstance(__version__, str)
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
.venv\Scripts\pytest tests/test_version.py -v
```

Expected: `ImportError: No module named 'version'`

- [ ] **Step 3: Create version.py**

```python
__version__ = "1.0.0"
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
.venv\Scripts\pytest tests/test_version.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Verify full suite still passes**

```powershell
.venv\Scripts\pytest tests/ -v
```

Expected: 28 PASSED (26 existing + 2 new)

- [ ] **Step 6: Commit**

```
git add version.py tests/test_version.py
git commit -m "feat: version.py as single source of truth for app version"
```

---

### Task 2: updater.py

**Files:**
- Create: `updater.py`
- Create: `tests/test_updater.py`

**Interfaces:**
- Consumes: `from version import __version__`
- Produces:
  - `check_for_update() -> str | None` — returns new version e.g. `"1.1.0"`, or `None`
  - `download_update(version: str, progress_cb: Callable[[int], None]) -> Path` — downloads to `%TEMP%`, calls `progress_cb(0–100)`
  - `launch_installer(setup_path: Path) -> None` — `subprocess.Popen`, no exit
  - `_parse_version(v: str) -> list[int]` — internal helper, tested directly
  - `_temp_setup_path(version: str) -> Path` — internal helper, mockable in tests

- [ ] **Step 1: Write failing tests**

```python
# tests/test_updater.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


def _mock_urlopen(tag_name: str):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({'tag_name': tag_name}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_parse_version_strips_v_prefix():
    import updater
    assert updater._parse_version('v1.2.3') == [1, 2, 3]


def test_parse_version_no_prefix():
    import updater
    assert updater._parse_version('1.0.0') == [1, 0, 0]


def test_check_for_update_returns_version_when_newer(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', return_value=_mock_urlopen('v1.1.0'))
    with patch.object(updater, '__version__', '1.0.0'):
        result = updater.check_for_update()
    assert result == '1.1.0'


def test_check_for_update_returns_none_when_same(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', return_value=_mock_urlopen('v1.0.0'))
    with patch.object(updater, '__version__', '1.0.0'):
        result = updater.check_for_update()
    assert result is None


def test_check_for_update_returns_none_when_older(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', return_value=_mock_urlopen('v0.9.0'))
    with patch.object(updater, '__version__', '1.0.0'):
        result = updater.check_for_update()
    assert result is None


def test_check_for_update_returns_none_on_network_error(mocker):
    import updater
    mocker.patch('urllib.request.urlopen', side_effect=Exception('network error'))
    result = updater.check_for_update()
    assert result is None


def test_download_update_calls_progress_cb(mocker, tmp_path):
    import updater
    dest = tmp_path / 'mtk-noise-canceller-setup.exe'
    progress_values = []

    def fake_urlretrieve(url, destpath, reporthook):
        reporthook(1, 500_000, 1_000_000)  # 50%
        reporthook(2, 500_000, 1_000_000)  # 100%
        return str(destpath), {}

    mocker.patch('urllib.request.urlretrieve', side_effect=fake_urlretrieve)
    mocker.patch('updater._temp_setup_path', lambda v: dest)

    updater.download_update('1.1.0', progress_values.append)
    assert 50 in progress_values
    assert 100 in progress_values


def test_download_update_returns_path(mocker, tmp_path):
    import updater
    dest = tmp_path / 'mtk-noise-canceller-setup.exe'
    mocker.patch('urllib.request.urlretrieve', return_value=(str(dest), {}))
    mocker.patch('updater._temp_setup_path', lambda v: dest)
    result = updater.download_update('1.1.0', lambda p: None)
    assert result == dest


def test_launch_installer_calls_popen(mocker):
    import updater
    mock_popen = mocker.patch('subprocess.Popen')
    updater.launch_installer(Path('C:/temp/setup.exe'))
    mock_popen.assert_called_once_with(['C:/temp/setup.exe'])
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
.venv\Scripts\pytest tests/test_updater.py -v
```

Expected: `ImportError: No module named 'updater'`

- [ ] **Step 3: Create updater.py**

```python
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable

from version import __version__

_REPO = "edinhograno/mtk-supression"
_ASSET = "mtk-noise-canceller-setup.exe"
_API_URL = f"https://api.github.com/repos/{_REPO}/releases/latest"


def _parse_version(v: str) -> list[int]:
    return [int(x) for x in v.lstrip('v').split('.')]


def _temp_setup_path(version: str) -> Path:
    return Path(tempfile.gettempdir()) / _ASSET


def check_for_update() -> str | None:
    try:
        req = urllib.request.Request(_API_URL, headers={'User-Agent': 'mtk-noise-canceller'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        tag = data['tag_name']
        if _parse_version(tag) > _parse_version(__version__):
            return tag.lstrip('v')
        return None
    except Exception:
        return None


def download_update(version: str, progress_cb: Callable[[int], None]) -> Path:
    url = f"https://github.com/{_REPO}/releases/download/v{version}/{_ASSET}"
    dest = _temp_setup_path(version)

    def reporthook(block_count: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            pct = min(100, block_count * block_size * 100 // total_size)
            progress_cb(pct)

    urllib.request.urlretrieve(url, str(dest), reporthook)
    return dest


def launch_installer(setup_path: Path) -> None:
    subprocess.Popen([str(setup_path)])
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
.venv\Scripts\pytest tests/test_updater.py -v
```

Expected: 9 PASSED

- [ ] **Step 5: Run full suite**

```powershell
.venv\Scripts\pytest tests/ -v
```

Expected: 37 PASSED

- [ ] **Step 6: Commit**

```
git add updater.py tests/test_updater.py
git commit -m "feat: updater — GitHub Releases API check, download, and launcher"
```

---

### Task 3: settings_ui.py — Update Banner

**Files:**
- Modify: `settings_ui.py`

**Interfaces:**
- Consumes: `updater.download_update(version, progress_cb) -> Path`
- Consumes: `updater.launch_installer(path) -> None`
- Consumes: `self._cmd_queue` (existing `queue.Queue`) — sends `'quit'` after installer launches
- Produces: `notify_update(version: str) -> None` — thread-safe, called from `main.py` background thread

- [ ] **Step 1: Add import at top of settings_ui.py**

Add `import threading` alongside the existing imports (it is not currently imported).

- [ ] **Step 2: Add new instance variables to `__init__`**

Extend `__init__` — add four new lines after `self._cmd_queue = None`:

```python
        self._pending_update_version: str | None = None
        self._update_version: str | None = None
        self._update_frame = None
        self._update_btn = None
        self._update_label = None
```

- [ ] **Step 3: Add banner frame to `_build()` and shift existing rows**

In `_build()`, immediately after `frame.grid()`, add the banner (it occupies row 0 and is hidden by default):

```python
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
```

Then shift all existing widget rows by +1:

| Old `row=` | New `row=` | Widget |
|-----------|-----------|--------|
| `row=0` | `row=1` | Microfone label |
| `row=0, columnspan=2` | `row=1, columnspan=2` | Microfone combobox |
| `row=1` | `row=2` | Intensidade label |
| `row=1` | `row=2` | Intensidade slider |
| `row=1` | `row=2` | Pct label |
| `row=2` | `row=3` | Autostart checkbox |
| `row=3` | `row=4` | Status label |
| `row=4` | `row=5` | Toggle button |

At the very end of `_build()`, after `self._refresh_btn()`, add:

```python
        if self._pending_update_version:
            self._show_update_banner(self._pending_update_version)
```

- [ ] **Step 4: Add update methods**

Append these methods to `SettingsUI` after `_refresh_btn`:

```python
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
        path = updater.download_update(self._update_version, self._on_download_progress)
        updater.launch_installer(path)
        if self._cmd_queue:
            self._cmd_queue.put('quit')

    def _on_download_progress(self, pct: int) -> None:
        if self._window is not None:
            self._window.after(0, lambda p=pct: self._update_btn.config(text=f'Baixando... {p}%'))
```

- [ ] **Step 5: Run full test suite**

```powershell
.venv\Scripts\pytest tests/ -v
```

Expected: 37 PASSED (no regressions — banner code has no unit tests, manual test below)

- [ ] **Step 6: Manual smoke test**

```powershell
.venv\Scripts\python main.py
```

1. App starts, no banner visible — correct
2. Right-click tray → Configurações — window opens, still no banner — correct
3. Close app

To verify the banner renders, add a temporary one-liner in `main.py` after `ui = SettingsUI(...)`:

```python
import threading; threading.Timer(2, lambda: ui.notify_update('9.9.9')).start()
```

Run again → open Settings after 2 s → banner "⬆ v9.9.9 disponível" must appear. Remove the temp line before committing.

- [ ] **Step 7: Commit**

```
git add settings_ui.py
git commit -m "feat: update banner in settings window with background download"
```

---

### Task 4: main.py — Background Update Check Thread

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `updater.check_for_update() -> str | None`
- Consumes: `ui.notify_update(version: str) -> None`

- [ ] **Step 1: Add imports**

Add at the top of `main.py` with existing imports:

```python
import time
import threading
import updater
```

- [ ] **Step 2: Add the update loop function**

Add before `def main()`:

```python
def _update_check_loop(ui: SettingsUI) -> None:
    while True:
        version = updater.check_for_update()
        if version:
            ui.notify_update(version)
            return
        time.sleep(86400)
```

- [ ] **Step 3: Start the thread in main()**

In `main()`, after `tray.run_in_thread()` and before `ui.run_main_loop(cmd_queue)`:

```python
    threading.Thread(target=_update_check_loop, args=(ui,), daemon=True).start()
```

- [ ] **Step 4: Add SettingsUI to the import line**

`SettingsUI` is already imported. The type hint in `_update_check_loop` is for readability only — Python 3.14 doesn't enforce it at runtime.

- [ ] **Step 5: Run full test suite**

```powershell
.venv\Scripts\pytest tests/ -v
```

Expected: 37 PASSED

- [ ] **Step 6: Manual test — no update available**

```powershell
.venv\Scripts\python main.py
```

App starts without errors, no banner appears. No exception in console. Close app.

- [ ] **Step 7: Commit**

```
git add main.py
git commit -m "feat: background update check on startup and every 24h"
```

---

### Task 5: build.spec — Remove uac_admin

**Files:**
- Modify: `build.spec`

**Interfaces:**
- None — build config change only

**Why:** `uac_admin=True` forces a UAC prompt on every launch. VB-Cable installation already uses PowerShell `Start-Process -Verb RunAs` in `vbcable_setup.py`, which triggers UAC only for the VB-Cable subprocess. The app itself does not need admin.

- [ ] **Step 1: Change uac_admin in build.spec**

In `build.spec`, inside the `EXE(...)` call, change:

```python
    uac_admin=True,
```

to:

```python
    uac_admin=False,
```

- [ ] **Step 2: Build exe and verify no UAC on launch**

```powershell
.venv\Scripts\pyinstaller build.spec
```

Expected: `dist\mtk-noise-canceller.exe` created without errors.

Run `dist\mtk-noise-canceller.exe` — Windows must NOT show a UAC prompt. Tray icon appears.

- [ ] **Step 3: Commit**

```
git add build.spec
git commit -m "chore: remove uac_admin — VB-Cable UAC handled by subprocess"
```

---

### Task 6: Inno Setup Script

**Files:**
- Create: `installer/mtk.iss`
- Modify: `.gitignore` (add `installer/Output/`)

**Interfaces:**
- Consumes: `dist\mtk-noise-canceller.exe` (PyInstaller output — must exist before ISCC runs)
- Produces: `installer\Output\mtk-noise-canceller-setup.exe`

**Prerequisite:** Inno Setup 6 installed. Download from https://jrsoftware.org/isinfo.php (free). Default path: `C:\Program Files (x86)\Inno Setup 6\`.

**Note on VB-Cable:** The Inno Setup script does NOT bundle VB-Cable. The app handles VB-Cable installation on first run via `first_run.py` + `vbcable_setup.py` (uses PowerShell UAC elevation for the driver installer subprocess).

- [ ] **Step 1: Create installer/mtk.iss**

```ini
; installer/mtk.iss
[Setup]
AppName=MTK Noise Canceller
AppVersion=1.0.0
AppPublisher=Mobiltracker
AppPublisherURL=https://github.com/edinhograno/mtk-supression
DefaultDirName={autopf}\MTK Noise Canceller
DefaultGroupName=MTK Noise Canceller
OutputDir=Output
OutputBaseFilename=mtk-noise-canceller-setup
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=MTK Noise Canceller
DisableProgramGroupPage=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\mtk-noise-canceller.exe"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{app}\mtk-noise-canceller.exe"; \
  Flags: postinstall nowait skipifsilent; \
  Description: "Iniciar MTK Noise Canceller"

[Icons]
Name: "{group}\MTK Noise Canceller"; Filename: "{app}\mtk-noise-canceller.exe"
Name: "{group}\Desinstalar MTK Noise Canceller"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
```

- [ ] **Step 2: Add installer/Output/ to .gitignore**

Open `.gitignore` and add at the end:

```
installer/Output/
```

- [ ] **Step 3: Build exe first (if not already built)**

```powershell
.venv\Scripts\pyinstaller build.spec
```

- [ ] **Step 4: Compile installer and verify output**

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\mtk.iss
```

Expected: `installer\Output\mtk-noise-canceller-setup.exe` created, no errors.

- [ ] **Step 5: Manual install test**

Run `installer\Output\mtk-noise-canceller-setup.exe`:
- UAC prompt appears (once, for installer elevation)
- App installs to `C:\Program Files\MTK Noise Canceller\`
- Start Menu shortcut created under MTK Noise Canceller group
- App launches after install (no UAC prompt — app runs as normal user)
- App appears in Settings → Apps → Installed apps as "MTK Noise Canceller"
- Uninstall from Apps list works cleanly

- [ ] **Step 6: Commit**

```
git add installer/mtk.iss .gitignore
git commit -m "feat: Inno Setup installer script"
```

---

### Task 7: build.ps1 + release.ps1 — Pipeline Update

**Files:**
- Modify: `build.ps1`
- Modify: `release.ps1`

**Interfaces:**
- `build.ps1`: reads `__version__` from `version.py` via Python, injects into `installer/mtk.iss` `AppVersion=` line, then calls ISCC
- `release.ps1`: uploads `installer\Output\mtk-noise-canceller-setup.exe` as release asset named `mtk-noise-canceller-setup.exe`

- [ ] **Step 1: Replace build.ps1 content**

```powershell
param(
    [switch]$Clean,
    [switch]$SkipInstaller
)

$root = $PSScriptRoot
Set-Location $root

if ($Clean) {
    Remove-Item -Recurse -Force "$root\dist", "$root\build" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$root\installer\Output" -ErrorAction SilentlyContinue
    Write-Host "Cleaned dist/, build/, installer/Output/"
}

Write-Host "Building exe..."
& .venv\Scripts\pyinstaller build.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$exe = "$root\dist\mtk-noise-canceller.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build finished but exe not found" -ForegroundColor Yellow
    exit 1
}
$exeSize = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "Exe -> dist\mtk-noise-canceller.exe ($exeSize MB)" -ForegroundColor Green

if ($SkipInstaller) {
    Write-Host "Skipping installer (-SkipInstaller)" -ForegroundColor Yellow
    exit 0
}

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    Write-Host "Inno Setup not found at: $iscc" -ForegroundColor Yellow
    Write-Host "Install from https://jrsoftware.org/isinfo.php or use -SkipInstaller" -ForegroundColor Yellow
    exit 1
}

$version = & .venv\Scripts\python -c "from version import __version__; print(__version__)"
$issPath = "$root\installer\mtk.iss"
(Get-Content $issPath) -replace 'AppVersion=.*', "AppVersion=$version" |
    Set-Content $issPath -Encoding utf8
Write-Host "Injected version $version into mtk.iss"

Write-Host "Building installer..."
& $iscc $issPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "ISCC FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$setup = "$root\installer\Output\mtk-noise-canceller-setup.exe"
if (Test-Path $setup) {
    $setupSize = [math]::Round((Get-Item $setup).Length / 1MB, 1)
    Write-Host "OK -> installer\Output\mtk-noise-canceller-setup.exe ($setupSize MB)" -ForegroundColor Green
}
```

- [ ] **Step 2: Update release.ps1 — change asset path and name**

In `release.ps1`, change:

```powershell
$exe  = "$PSScriptRoot\dist\mtk-noise-canceller.exe"
```

to:

```powershell
$exe  = "$PSScriptRoot\installer\Output\mtk-noise-canceller-setup.exe"
```

Change the error message:

```powershell
if (-not (Test-Path $exe)) {
    Write-Host "ERRO: setup.exe nao encontrado. Rode .\build.ps1 primeiro." -ForegroundColor Red
    exit 1
}
```

Change the upload URL asset name:

```powershell
-Uri "${uploadUrl}?name=mtk-noise-canceller-setup.exe" `
```

- [ ] **Step 3: Test full build pipeline**

```powershell
.\build.ps1 -Clean
```

Expected output:
```
Cleaned dist/, build/, installer/Output/
Building exe...
...
Exe -> dist\mtk-noise-canceller.exe (XX MB)
Injected version 1.0.0 into mtk.iss
Building installer...
...
OK -> installer\Output\mtk-noise-canceller-setup.exe (XX MB)
```

- [ ] **Step 4: Run full test suite**

```powershell
.venv\Scripts\pytest tests/ -v
```

Expected: 37 PASSED

- [ ] **Step 5: Commit**

```
git add build.ps1 release.ps1
git commit -m "chore: build pipeline generates setup.exe via Inno Setup"
```

---

## Release Workflow (Post-Implementation)

When ready to ship a new version:

```powershell
# 1. Bump version
# Edit version.py: __version__ = "1.1.0"

# 2. Commit + tag
git add version.py
git commit -m "chore: bump version to 1.1.0"
git tag v1.1.0
git push && git push --tags

# 3. Build
.\build.ps1 -Clean

# 4. Publish
.\release.ps1 -Tag v1.1.0
```

Users on v1.0.0 will see the update banner within 24h of release.
