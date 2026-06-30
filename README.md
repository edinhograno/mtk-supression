# MTK Noise Canceller

Cancelamento de ruído de microfone para Windows via VB-Cable. Filtra ruído ambiente em tempo real antes de enviar áudio para Discord, Teams, Zoom ou qualquer app de comunicação.

---

## Como funciona

```
Microfone → [MTK Noise Canceller] → CABLE Input (VB-Cable) → Discord/Teams
```

O app captura o áudio do microfone, aplica filtro de ruído (highpass + noise gate via [pedalboard](https://github.com/spotify/pedalboard)) e redireciona para o driver virtual VB-Cable. No Discord/Teams, você seleciona **CABLE Output** como microfone.

---

## Instalação

1. Baixe `mtk-noise-canceller.exe` na [página de releases](https://github.com/edinhograno/mtk-supression/releases)
2. Execute como administrador
3. Na primeira execução, o app baixa e instala o driver **VB-Cable** automaticamente (~5 MB)
4. Selecione seu microfone na janela de configurações
5. Configure Discord/Teams para usar **CABLE Output** como microfone

> **Requisitos:** Windows 10/11 (64-bit) · Conexão com internet na primeira execução

---

## Configuração no Discord

1. Abra Discord → Configurações → Voz e Vídeo
2. Em **Dispositivo de entrada**, selecione `CABLE Output (VB-Audio Virtual Cable)`
3. Fale normalmente — o filtro já está ativo

---

## Interface

A janela de configurações permite:

| Opção | Descrição |
|---|---|
| **Microfone** | Seleciona o microfone físico de entrada |
| **Intensidade** | Nível do filtro de ruído (0–100%) |
| **Iniciar com Windows** | Autostart via registro do Windows |
| **Ativar / Desativar** | Liga/desliga o filtro sem fechar o app |

O app fica minimizado na **bandeja do sistema** (system tray). Clique com botão direito para abrir configurações ou sair.

---

## Build (desenvolvimento)

```powershell
# Instalar dependências
pip install -r requirements.txt

# Build (gera dist\mtk-noise-canceller.exe)
.\build.ps1

# Build limpo
.\build.ps1 -Clean
```

**Dependências principais:** Python 3.12 · pedalboard · sounddevice · pystray · Pillow

---

## Tecnologia

- **Filtro de áudio:** [pedalboard](https://github.com/spotify/pedalboard) (Spotify) — HighpassFilter + NoiseGate
- **Áudio I/O:** [sounddevice](https://python-sounddevice.readthedocs.io/) / PortAudio
- **Driver virtual:** [VB-Cable](https://vb-audio.com/Cable/) (instalado automaticamente)
- **Empacotamento:** PyInstaller (onefile, UAC admin)

---

## Licença

MIT
