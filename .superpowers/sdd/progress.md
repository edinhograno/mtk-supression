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
