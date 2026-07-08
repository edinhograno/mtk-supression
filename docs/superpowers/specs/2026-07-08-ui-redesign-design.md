# UI Redesign — MTK Noise Canceller

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir a UI tkinter genérica por uma interface PySide6 moderna, minimalista e com identidade visual, mantendo toda a lógica de negócio intacta.

**Architecture:** Rewrite de `settings_ui.py`, `first_run.py` e `tray.py` para PySide6. A lógica de áudio (`audio_engine.py`), configuração (`config.py`), updater (`updater.py`) e VB-Cable (`vbcable_setup.py`) não muda. Um novo módulo `style.py` centraliza cores e QSS para evitar duplicação.

**Tech Stack:** PySide6 6.x, PIL/Pillow (já presente), pystray (mantido para bandeja).

---

## Global Constraints

- Python 3.14, Windows 10/11 64-bit
- PySide6 deve ser adicionado ao `requirements.txt` e ao `build.spec` (`hiddenimports`)
- Nenhuma alteração em `audio_engine.py`, `config.py`, `updater.py`, `vbcable_setup.py`, `main.py`
- A interface pública de `SettingsUI` não muda: `__init__(config, engine, show_on_start)`, `run_main_loop(cmd_queue)`, `request_show()`, `request_quit()`, `notify_update(version)`
- A interface pública de `TrayApp` não muda: `__init__(config, engine, on_settings, on_quit)`, `run_in_thread()`, `update_icon()`
- A interface pública de `first_run.py` não muda: `run_if_needed(config) -> bool`
- Janela fecha para bandeja (não encerra o app) ao clicar no X
- Thread-safety: toda atualização de UI de threads de fundo via `QMetaObject.invokeMethod(..., Qt.QueuedConnection)` ou `QTimer.singleShot(0, fn)`
- Sem testes unitários para UI (Qt mainloop incompatível com pytest headless)
- PyInstaller onefile: PySide6 requer plugins Qt — adicionar ao `build.spec`

---

## Paleta de cores

| Token | Valor | Uso |
|-------|-------|-----|
| `COLOR_ACCENT` | `#0078D4` | Slider, checkbox, combobox focus |
| `COLOR_ACTIVE` | `#1a7a36` | Borda/texto quando filtro ativo |
| `COLOR_INACTIVE` | `#c0392b` | Borda/texto quando filtro inativo |
| `COLOR_BG` | `#ffffff` | Fundo da janela |
| `COLOR_CARD` | `#f8f9fa` | Fundo dos cards de controle |
| `COLOR_BORDER` | `#eeeeee` | Borda dos cards |
| `COLOR_TEXT` | `#222222` | Texto principal |
| `COLOR_MUTED` | `#999999` | Labels "MICROFONE", "INTENSIDADE" |

---

## Arquivos

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `style.py` | Criar | Constantes de cor + QSS stylesheet centralizado |
| `settings_ui.py` | Reescrever | Janela de configurações (PySide6) |
| `first_run.py` | Reescrever | Wizard de primeira execução (PySide6) |
| `tray.py` | Modificar | `_make_icon` → orelha desenhada com PIL |
| `requirements.txt` | Modificar | Adicionar `PySide6>=6.6` |
| `build.spec` | Modificar | `hiddenimports` e Qt plugins para PySide6 |
| `main.py` | Sem alteração | Interface pública de `SettingsUI` e `first_run.run_if_needed` preservada |

---

## Design da janela de configurações

**Dimensões:** ~340×300px, `setFixedSize`, sem resize, sem maximize.

**Layout (de cima para baixo):**

1. **Banner de update** — `QFrame` oculto por padrão. Quando visível: ícone ⬆, texto "v1.x.x disponível", botão "Atualizar agora". Fundo `#e6f4ea`, texto `#1a7a36`.

2. **Power button** — `QPushButton` circular 64×64px com ícone de orelha (emoji 👂 ou SVG). Ao clicar, liga/desliga o filtro. Borda e fundo mudam conforme estado:
   - Ativo: `border: 3px solid #1a7a36; background: #f0fdf4`
   - Inativo: `border: 3px solid #c0392b; background: #fef2f2`

3. **Status label** — texto "● ATIVO" (verde) ou "● INATIVO" (vermelho), `font-weight: 700`, `font-size: 11px`, centralizado abaixo do botão.

4. **Card Microfone** — `QFrame` com `border-radius: 8px; background: #f8f9fa; border: 1px solid #eeeeee`. Contém: label "MICROFONE" (10px, muted), `QComboBox` com lista de dispositivos de entrada (sem CABLE). Ao mudar: para engine, troca device, reinicia se estava ativo.

5. **Card Intensidade** — mesmo estilo de card. Contém: label "INTENSIDADE" + valor "75%" em azul, `QSlider` horizontal (0–100). Ao soltar: salva config e chama `engine.set_intensity()`.

6. **Rodapé** — `QCheckBox` "Iniciar com Windows" alinhado à esquerda. Ao mudar: escreve/apaga chave `HKCU\...\Run\MTKNoiseCanceller`.

**Comportamento:**
- Fechar janela (`closeEvent`) → `hide()`, não encerra
- `request_show()` → `show(); raise_(); activateWindow()`
- `run_main_loop(cmd_queue)` → cria `QApplication.instance() or QApplication(sys.argv)`, constrói janela (oculta se `show_on_start=False`), inicia `QTimer` de 100ms para poll do `cmd_queue`, chama `app.exec()` (bloqueante, igual ao `mainloop()` do tkinter)
- `request_quit()` → `cmd_queue.put('quit')` → `engine.stop(); app.quit()`
- `run_if_needed` em `first_run.py` também usa `QApplication.instance() or QApplication(sys.argv)` — reutiliza a instância se já existir, cria se não existir. `main.py` não precisa de alterações.

---

## Design do ícone de bandeja

**Implementação:** PIL desenha bitmap 64×64 RGBA, passado ao pystray.

**Ativo (verde):**
- Fundo transparente
- Forma de orelha desenhada com `ImageDraw` usando curvas (Bezier aproximado com `arc` + `line`)
- Cor: `#1a7a36` (verde)
- Sem ornamentos adicionais

**Inativo (vermelho):**
- Mesma forma de orelha
- Cor: `#c0392b` (vermelho)
- Linha diagonal (canto superior esquerdo ao inferior direito) sobre a orelha, stroke vermelho escuro, indica "desligado"

A função `_make_icon(active: bool) -> Image.Image` em `tray.py` é reescrita para produzir essa orelha. O resto de `TrayApp` não muda.

---

## Design do wizard de primeira execução

**Trigger:** `config.get('first_run', True) == True`

**Tela 1 — Bem-vindo:** `QDialog` modal, 400×260px, mesmo estilo da janela principal. Título "MTK Noise Canceller", ícone de orelha grande (96px), texto "Bem-vindo! Precisamos instalar o VB-Cable para processar o áudio." Botão "Continuar".

**Tela 2 — Instalando VB-Cable:** `QProgressBar` indeterminada durante o download/install do VB-Cable (processo em thread separada). Texto de status atualizado via signal. Se falhar: mensagem de erro + botão "Tentar novamente" / "Cancelar".

**Tela 3 — Autostart:** Texto "Deseja que o MTK Noise Canceller inicie automaticamente com o Windows?". Dois botões: "Sim" / "Não". Salva config e registro.

**Tela 4 — Pronto:** "Instalação completa! O filtro já está ativo." Botão "Fechar".

`run_if_needed(config) -> bool`: usa `QApplication.instance() or QApplication(sys.argv)` (não fecha o app ao terminar — apenas fecha o wizard), exibe wizard modal, retorna `True` se completo, `False` se cancelado.

---

## `style.py`

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
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        image: url(:/checkmark);
    }}
    """
```
