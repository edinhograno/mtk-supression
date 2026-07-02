# Design: Inno Setup Installer + Auto-Update — MTK Noise Canceller

**Data:** 2026-07-02  
**Status:** Aprovado  
**Repo:** github.com/edinhograno/mtk-supression (público)

---

## Motivação

- `--onefile` PyInstaller exe trigga Windows Defender em algumas máquinas ("Could not load PKG archive")
- `uac_admin=True` no build.spec força UAC em todo launch, mesmo após VB-Cable instalado
- Sem mecanismo de atualização: usuários ficam em versões antigas indefinidamente

---

## Arquitetura

```
version.py          → __version__ = "1.0.0"  (source of truth)
updater.py          → checa GitHub API, baixa setup.exe, lança installer
settings_ui.py      → recebe callback, mostra banner + botão de update
main.py             → dispara check no startup + agenda check diário (86400s)
installer/mtk.iss   → Inno Setup: instala app + VB-Cable, atalhos, uninstaller
build.spec          → remove uac_admin=True
build.ps1           → pyinstaller → ISCC → setup.exe
release.ps1         → publica setup.exe no GitHub Releases
```

---

## Componentes

### `version.py`

```python
__version__ = "1.0.0"
```

Sem dependências. Importado por `updater.py`. Versão atualizada manualmente antes de cada release; `build.ps1` lê o valor para injetar no `.iss`.

---

### `updater.py`

Três funções públicas, sem dependências externas (só stdlib):

**`check_for_update() -> str | None`**
- GET `https://api.github.com/repos/edinhograno/mtk-supression/releases/latest`
- Header `User-Agent: mtk-noise-canceller` (obrigatório pela GitHub API)
- Timeout: 10s
- Compara `tag_name` (ex: `"v1.1.0"`) com `__version__` via split em inteiros
- Retorna string da nova versão ou `None` (sem update ou erro de rede)

**`download_update(version: str, progress_cb: Callable[[int], None]) -> Path`**
- URL: `https://github.com/edinhograno/mtk-supression/releases/download/v{version}/mtk-noise-canceller-setup.exe`
- Destino: `%TEMP%\mtk-noise-canceller-setup.exe`
- `urllib.request.urlretrieve` com reporthook → chama `progress_cb(pct)` onde `pct` é 0–100
- Retorna `Path` do arquivo baixado

**`launch_and_exit(setup_path: Path) -> None`**
- `subprocess.Popen([str(setup_path)])`
- `sys.exit(0)`

---

### `settings_ui.py` — mudanças

Banner frame adicionado no topo da janela, oculto por padrão (`frame.grid_remove()`).

**Layout com banner visível:**
```
┌─────────────────────────────────────────────┐
│ ⬆ v1.1.0 disponível    [Atualizar agora]   │
├─────────────────────────────────────────────┤
│ Microfone: [...]                            │
│ Intensidade: ──────●──  75%                 │
│ ☑ Iniciar com Windows                       │
│ ● Ativo                                     │
│ [Desativar]                                 │
└─────────────────────────────────────────────┘
```

**Novos métodos:**

`notify_update(version: str)` — pode ser chamado de qualquer thread via `window.after(0, ...)`:
- Atualiza label com versão
- Exibe o banner frame

`_on_update_click()`:
- Desabilita botão, texto "Baixando... 0%"
- Thread: `updater.download_update(version, progress_cb)`
- `progress_cb` usa `window.after(0, ...)` para atualizar botão: "Baixando... N%"
- Ao completar: `updater.launch_and_exit(path)` → app fecha

---

### `main.py` — mudanças

```python
# após engine.start():
threading.Thread(target=_check_update_loop, args=(ui,), daemon=True).start()

def _check_update_loop(ui):
    while True:
        version = updater.check_for_update()
        if version:
            ui.notify_update(version)
            return  # não checa de novo se update encontrado
        time.sleep(86400)  # 1x por dia
```

Check no startup (imediato) + a cada 24h se app ficar aberto. Para após encontrar update.

---

### `installer/mtk.iss`

```ini
[Setup]
AppName=MTK Noise Canceller
AppVersion=1.0.0
AppPublisher=Mobiltracker
DefaultDirName={pf}\MTK Noise Canceller
DefaultGroupName=MTK Noise Canceller
OutputDir=Output
OutputBaseFilename=mtk-noise-canceller-setup
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\dist\mtk-noise-canceller.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\VBCABLE_Setup_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{tmp}\VBCABLE_Setup_x64.exe"; Parameters: "/S"; Flags: runhidden waituntilterminated; \
  Description: "Instalando driver VB-Cable..."
Filename: "{app}\mtk-noise-canceller.exe"; Flags: postinstall nowait skipifsilent; \
  Description: "Iniciar MTK Noise Canceller"

[Icons]
Name: "{group}\MTK Noise Canceller"; Filename: "{app}\mtk-noise-canceller.exe"
Name: "{group}\Desinstalar MTK Noise Canceller"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
```

`build.ps1` injeta a versão atual (lida de `version.py`) no campo `AppVersion=` antes de chamar ISCC.

---

### `build.ps1` — mudanças

Após `pyinstaller build.spec`:

```powershell
# lê versão
$version = (python -c "from version import __version__; print(__version__)")

# injeta no .iss
(Get-Content installer\mtk.iss) -replace 'AppVersion=.*', "AppVersion=$version" |
    Set-Content installer\mtk.iss

# compila installer
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
& $iscc installer\mtk.iss
# output: installer\Output\mtk-noise-canceller-setup.exe
```

Pré-requisito: **Inno Setup 6** instalado na máquina de build (não vai no repo).

---

### `build.spec` — mudança

```python
# Remove:
uac_admin=True,
# App passa a rodar sem UAC; elevação fica exclusivamente no installer
```

---

### `release.ps1` — mudança

Path do asset muda de `dist\mtk-noise-canceller.exe` para `installer\Output\mtk-noise-canceller-setup.exe`.

---

## Fluxo de Release

```
1. Atualiza __version__ em version.py
2. git commit + tag vX.Y.Z + push
3. .\build.ps1        → gera exe + setup.exe
4. .\release.ps1 -Tag vX.Y.Z  → cria release no GitHub, upload setup.exe
```

---

## Fluxo do Usuário Final

**Primeira instalação:**
1. Baixa `mtk-noise-canceller-setup.exe` do GitHub Releases
2. Executa → UAC (uma vez) → instala VB-Cable + app → atalho Start Menu
3. App inicia sem UAC; first-run wizard pula VB-Cable (já instalado) → pede mic

**Update:**
1. App detecta nova versão no startup
2. Abre Settings → banner "v1.1.0 disponível" + [Atualizar agora]
3. Clica → baixa setup.exe → lança → app fecha → installer roda → app volta

---

## Fora de Escopo

- Assinatura de código (code signing certificate)
- Rollback de versão
- Canal beta/stable separado
- Suporte a update silencioso (sem interação do usuário)
