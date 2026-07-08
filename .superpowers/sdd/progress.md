# SDD Progress — MTK Noise Canceller

## Tasks

| Task | Description | Status | Commit(s) | Notes |
|------|-------------|--------|-----------|-------|
| 1 | Project scaffold | complete | b23d6db..57692f4 | |
| 2 | Config (load/save/defaults) | complete | 57692f4..57092c7 | |
| 3 | NoiseFilter | complete | 57092c7..16e1af0 | Backend switched to pedalboard (see Task 9) |
| 4 | AudioEngine | complete | 16e1af0..c90513a | |
| 5 | VB-Cable setup | complete | c90513a..e4c151c | UAC via PowerShell Start-Process -Verb RunAs |
| 6 | First-run wizard | complete | e4c151c..bd3e6d0 | |
| 7 | Tray icon (daemon thread) | complete | fd91b3b | |
| 8 | Settings window (tkinter + queue) | complete | df1f48c | No unit tests — tkinter mainloop incompatible with CI |
| 9 | main.py + manual test | complete | 415d9df | pedalboard 0.9.23 replaced noisereduce (Python 3.14 compat) |
| 10 | PyInstaller packaging | pending | — | build.spec, onefile exe, pedalboard hiddenimports |

## Deviations from Original Plan

- `rnnoise` incompatível com Python 3.14 → substituído por **pedalboard 0.9.23** (`HighpassFilter` + `NoiseGate`)
- VB-Cable install usa `Start-Process -Verb RunAs` (UAC elevation) em vez de subprocess direto
- Task 8 sem testes unitários: `tkinter.mainloop()` não executa em ambiente CI headless

## Plano: Installer + Auto-Update (2026-07-02)

| Task | Descrição | Status | Commits | Notes |
|------|-----------|--------|---------|-------|
| 1 | version.py | complete | fe7281d..d887029 | review clean |
| 2 | updater.py | complete | d887029..b24aff6 | review clean, fix: str() vs as_posix() |
| 3 | settings_ui.py — update banner | complete | b24aff6..17685e8 | review clean |
| 4 | main.py — update check thread | complete | 17685e8..9146ca8 | review clean |
| 5 | build.spec — remove uac_admin | complete | 9146ca8..01192ed | review clean |
| 6 | Inno Setup script | complete | 01192ed..a68d30e | review clean (finding AppId syntax = false positive — {{GUID} is correct Inno Setup convention) |
| 7 | build.ps1 + release.ps1 pipeline | complete | a68d30e..1e8f6dd | review clean; minor: null-Trim on Python fail (acceptable) |
| FR | Final review fix: download error handling | complete | 1e8f6dd..a1d386e | Important finding fixed |

## Minor findings from final review (not blocking)
- release.ps1 notes text says "run as administrator" / "download VB-Cable" — outdated, fix before first public release
- build.ps1 mutates mtk.iss in-place after version inject — leaves file dirty in git after build; low priority

## Plano: Virtual Device Identity (2026-07-08)

| Task | Descrição | Status | Commits | Notes |
|------|-----------|--------|---------|-------|
| 1 | virtual_device.py + requirements.txt + tests | complete | 971a616..b43061e | review clean; minor: CLSCTX_ALL unused, PropVariantClear leak on non-VT_LPWSTR (no-op in practice), loose SetValue assert |
| 2 | Wire vbcable_setup.py + audio_engine.py + build.spec | pending | — | |

## Minor findings Task 1 (not blocking)
- virtual_device.py: CLSCTX_ALL imported but unused
- virtual_device.py _get_friendly_name: PropVariantClear not called on non-VT_LPWSTR path (safe in practice)
- test_virtual_device.py test_rename_cable_output_calls_set_value_and_commit: SetValue args not verified
