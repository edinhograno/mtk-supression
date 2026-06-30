# Próximos Passos — MTK Noise Canceller

## Estado atual (2026-06-30)

### Tarefas concluídas
| Task | Descrição | Commits |
|------|-----------|---------|
| 1 | Scaffold do projeto | b23d6db..57692f4 |
| 2 | Config (load/save/defaults) | 57692f4..57092c7 |
| 3 | NoiseFilter | 57092c7..16e1af0 |
| 4 | AudioEngine | 16e1af0..c90513a |
| 5 | VB-Cable setup | c90513a..e4c151c |
| 6 | First-run wizard | e4c151c..bd3e6d0 |
| 7 | Tray icon (daemon thread) | fd91b3b |
| 8 | Settings window (tkinter + queue) | df1f48c |
| 9 | main.py + teste manual | 415d9df |

### Desvios do plano original
- `rnnoise` incompatível com Python 3.14 → substituído por **pedalboard 0.9.23** (`HighpassFilter` + `NoiseGate`)
- VB-Cable install usa PowerShell `Start-Process -Verb RunAs` (UAC) em vez de subprocess direto
- `progress.md` precisa ser atualizado para Tasks 8 e 9 (só vai até Task 7)

---

## Próxima sessão

### 1. Verificar qualidade do filtro (5 min)
Se ainda não testado após o reset: rodar `main.py`, selecionar microfone, ativar, falar no Discord/Teams com "CABLE Output" como mic de entrada. A voz deve passar limpa, sem o efeito de "mata voz" do noisereduce.

Se qualidade ruim → ajustar `threshold_db` em `noise_filter.py:_apply_pedalboard` (atualmente: `-60 + intensity * 25`, range -60 a -35 dB).

### 2. Atualizar progress.md (2 min)
Arquivo: `.superpowers/sdd/progress.md`

Adicionar:
```
Task 8: complete (commit df1f48c, no unit tests — tkinter mainloop não roda em CI)
Task 9: complete (commit 415d9df, teste manual OK — pedalboard substituiu noisereduce)
```

### 3. Task 10: PyInstaller packaging

**Pré-requisito:** `pyinstaller` deve estar no venv.
```powershell
.venv\Scripts\pip install pyinstaller==6.21.0
```

**Passo 1:** Gerar ícone
```powershell
.venv\Scripts\python -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (64,64),(0,0,0,0))
ImageDraw.Draw(img).ellipse([4,4,60,60], fill=(0,160,0,255))
img.save('assets/icon.ico')
"
```

**Passo 2:** Criar `build.spec`
- Ponto de atenção: incluir `pedalboard` nos `hiddenimports` (não estava no plano original)
- Incluir `assets/VBCABLE_Setup_x64.exe` e `assets/icon.ico` nos `datas`

**Passo 3:** Build e teste
```powershell
.venv\Scripts\pyinstaller build.spec
.\dist\mtk-noise-canceller.exe
```

Verificar: `.exe` funciona igual ao `python main.py`, wizard roda, tray aparece, filtro funciona.

**Commit:**
```
chore: PyInstaller build spec for single-file exe distribution
```

---

## Prompt para continuar

Cole isso no início da próxima sessão:

> Projeto: MTK Noise Canceller (Python 3.14, Windows).
> Tasks 1-9 concluídas (veja PROXIMOS_PASSOS.md no root do projeto).
> Pendente: (1) atualizar .superpowers/sdd/progress.md para Tasks 8 e 9,
> (2) Task 10 — PyInstaller packaging com build.spec, incluindo pedalboard nos hiddenimports.
> Backend de noise agora é pedalboard (não rnnoise/noisereduce).
> Continua em portugues.
