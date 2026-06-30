# MTK Noise Canceller — Design Spec

**Date:** 2026-06-30  
**Status:** Approved

---

## Overview

Desktop app for Windows that captures microphone input, applies real-time noise suppression, and routes the clean audio to a VB-Cable virtual device so any app (Meet, Teams, Discord) can use it as a microphone.

Distributed internally as a single `.exe` file.

---

## Architecture

```
main.py             Entry point — initializes tray + first-run check
tray.py             System tray icon + right-click menu
first_run.py        First-run wizard: VB-Cable install + startup question
settings_ui.py      Settings window: mic selector, intensity slider, on/off
audio_engine.py     Audio processing loop (runs in background thread)
noise_filter.py     Noise suppression: RNNoise with noisereduce fallback
vbcable_setup.py    VB-Cable detection, download, and silent install
assets/icon.ico     Tray icon (green = active, red = inactive)
requirements.txt    Python dependencies
build.spec          PyInstaller build config
```

---

## Data Flow

```
Mic (physical) → sounddevice InputStream
    → noise_filter.apply(chunk, intensity)
        → RNNoise (primary, ~10ms latency)
        → noisereduce (fallback, ~50–150ms latency)
    → sounddevice OutputStream → CABLE Input (VB-Cable)
        → Meet / Teams / Discord (reads CABLE Output as mic)
```

---

## Components

### `vbcable_setup.py`
- Detects VB-Cable via `sounddevice.query_devices()` — looks for `CABLE Input`
- If absent: uses bundled `VBCABLE_Setup_x64.exe` (packed via PyInstaller `--add-data`)
- Runs installer with `/S` silent flag after user confirms

### `first_run.py`
- Runs on first launch (flag in `config.json`)
- Step 1: Check VB-Cable. If missing, show confirmation dialog:
  > "Este app precisa instalar um driver de áudio virtual (VB-Cable) para funcionar. Deseja instalar agora?"
  - Yes → install, show progress
  - No → show warning and exit
- Step 2: Ask startup preference:
  > "Deseja que o app inicie automaticamente com o Windows?"
  - Yes → write `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\MTKNoiseCanceller`
  - No → skip (user can enable later in settings)
- Marks `first_run: false` in config on completion

### `audio_engine.py`
- Runs in a `threading.Thread` (daemon)
- `sounddevice` InputStream reads selected mic in 20ms chunks
- Passes each chunk to `noise_filter.apply(chunk, intensity)`
- Writes result to `CABLE Input` via OutputStream
- Controlled by a `threading.Event` — UI calls `start()` / `stop()`

### `noise_filter.py`
- On init: attempts `import rnnoise_python`
  - Success → use RNNoise (~10ms latency, high quality)
  - Failure → fall back to `noisereduce` (~50–150ms, good for static noise)
- `apply(chunk: np.ndarray, intensity: float) -> np.ndarray`
  - `intensity` 0.0–1.0: linear blend between raw and filtered signal
  - 0.0 = passthrough, 1.0 = full filter

### `tray.py`
- Uses `pystray`
- Icon color: green (active) / red (inactive)
- Right-click menu: `Ativar / Desativar` | `Configurações` | `Sair`

### `settings_ui.py`
- Built with `tkinter` (stdlib, no extra dependency)
- Controls:
  - Dropdown: list of available input devices from `sounddevice.query_devices()`
  - Slider: 0–100% intensity (maps to 0.0–1.0 float)
  - Checkbox: "Iniciar com Windows"
  - Toggle button: Ativar / Desativar
  - Status label: "● Ativo" / "● Inativo"
- Changes persist immediately to `config.json`

### `config.json`
Stored at `~/.mtk-noise-canceller/config.json`:
```json
{
  "first_run": false,
  "input_device": "Microfone (Realtek HD Audio)",
  "intensity": 0.75,
  "autostart": true,
  "active": true
}
```

---

## UI Layout

```
┌─────────────────────────────────┐
│  MTK Noise Canceller            │
├─────────────────────────────────┤
│  Microfone: [Realtek HD ▼]      │
│                                 │
│  Intensidade: [====|====] 75%   │
│                                 │
│  [x] Iniciar com Windows        │
│                                 │
│  Status: ● Ativo                │
│                                 │
│        [Desativar]              │
└─────────────────────────────────┘
```

---

## Packaging

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico build.spec
```

- `--onefile`: single `.exe` output
- `--windowed`: no console window
- `--add-data`: bundles VB-Cable installer inside the `.exe`
- Output: `dist/mtk-noise-canceller.exe`

Target distribution: share `.exe` via internal channel (email, Teams, shared drive).

---

## Dependencies

```
sounddevice
numpy
noisereduce
rnnoise-python   # optional — graceful fallback if install fails
pystray
Pillow           # required by pystray for icon rendering
pyinstaller      # dev/build only
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| VB-Cable install refused | App exits with message |
| VB-Cable install fails | Shows error dialog, asks to retry or exit |
| RNNoise unavailable | Falls back to noisereduce silently |
| Selected mic disconnected | Shows tray notification, pauses engine |
| CABLE Input not found after install | Shows error, prompts reboot |

---

## Out of Scope (MVP)

- Audio monitoring / preview
- Noise profile visualization
- Multiple simultaneous input devices
- macOS / Linux support
- Auto-update mechanism
