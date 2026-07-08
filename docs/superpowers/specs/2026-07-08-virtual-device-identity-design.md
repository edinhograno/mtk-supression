# Virtual Device Identity — MTK Noise Canceller

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Após instalação do VB-Cable, renomear o dispositivo "CABLE Output" para "MTK Noise Canceller" no sistema Windows. Ao ligar o filtro, definir esse device como microfone padrão. Ao desligar ou sair, restaurar o device padrão anterior.

**Architecture:** Novo módulo `virtual_device.py` encapsula toda lógica COM (Windows Core Audio API via `comtypes`). `vbcable_setup.py` chama rename após install. `audio_engine.py` chama set/restore default no start/stop.

**Tech Stack:** Python 3.14, Windows 10/11 64-bit, `comtypes>=1.4`, Windows Core Audio API (IMMDeviceEnumerator, IPropertyStore, IPolicyConfigClient).

---

## Global Constraints

- Python 3.14, Windows 10/11 64-bit
- `comtypes>=1.4` adicionado ao `requirements.txt`
- Sem alteração em `main.py`, `config.py`, `settings_ui.py`, `first_run.py`, `tray.py`, `noise_filter.py`
- Interface pública de `AudioEngine` não muda: `start()`, `stop()`, `is_running()`, etc.
- Interface pública de `vbcable_setup.install()` não muda
- Rename é operação única na instalação (requer admin via UAC — o installer já eleva)
- Set/restore default é por-usuário, sem admin
- Se rename falhar: app continua funcionando, device fica como "CABLE Output", warning no log
- Se set/restore default falhar: app continua funcionando, warning no log
- Device padrão anterior armazenado em memória (`AudioEngine._prev_default_id`) — não persiste em config
- PyInstaller onefile: `comtypes` funciona frozen sem configuração extra

---

## Fluxo de dados

```
[Instalação — admin]
vbcable_setup.install()
  └─ virtual_device.rename_cable_output("MTK Noise Canceller")
       └─ IMMDeviceEnumerator → encontra CABLE Output → IPropertyStore(STGM_READWRITE)
            └─ SetValue(PKEY_Device_FriendlyName, "MTK Noise Canceller")

[Filtro ligado — sem admin]
audio_engine.start()
  └─ virtual_device.get_default_capture_id()        → salva em self._prev_default_id
  └─ virtual_device.find_device_id("MTK Noise Canceller", capture=True) → endpoint_id
  └─ virtual_device.set_as_default_capture(endpoint_id)
       └─ IPolicyConfigClient.SetDefaultEndpoint(id, eConsole)
       └─ IPolicyConfigClient.SetDefaultEndpoint(id, eCommunications)

[Filtro desligado — sem admin]
audio_engine.stop()
  └─ virtual_device.set_as_default_capture(self._prev_default_id)  [se não-None]
  └─ self._prev_default_id = None
```

---

## `virtual_device.py` — API completa

```python
MTK_DEVICE_NAME = "MTK Noise Canceller"
CABLE_OUTPUT_NAME = "CABLE Output"

def rename_cable_output(new_name: str = MTK_DEVICE_NAME) -> bool:
    """
    Renomeia o capture endpoint cujo nome contenha CABLE_OUTPUT_NAME.
    Usa IMMDevice.OpenPropertyStore(STGM_READWRITE) + SetValue(PKEY_Device_FriendlyName).
    Requer admin. Retorna True se renomeou, False se falhou (loga warning).
    """

def find_device_id(name_fragment: str, capture: bool = True) -> str | None:
    """
    Enumera endpoints (capture se capture=True, render se False).
    Retorna endpoint ID do primeiro device cujo FriendlyName contenha name_fragment.
    Retorna None se não encontrado.
    """

def get_default_capture_id() -> str | None:
    """
    Retorna endpoint ID do capture device padrão atual (eConsole).
    Retorna None se falhar.
    """

def set_as_default_capture(endpoint_id: str) -> bool:
    """
    Define endpoint_id como default capture para eConsole e eCommunications.
    Usa IPolicyConfigClient (undocumented COM, sem admin, por-usuário).
    Retorna True se OK, False se falhou (loga warning).
    """
```

---

## Interfaces COM necessárias

### IMMDeviceEnumerator
- `CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"`
- `IID_IMMDeviceEnumerator = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"`
- Métodos usados: `EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)`, `GetDefaultAudioEndpoint(eCapture, eConsole)`, `GetDevice(id)`

### IMMDeviceCollection
- Iteração via `GetCount()` + `Item(i)`

### IMMDevice
- Métodos usados: `GetId()`, `OpenPropertyStore(STGM_READ | STGM_READWRITE)`

### IPropertyStore
- `STGM_READ = 0x00000000` — para leitura de FriendlyName (find/get)
- `STGM_READWRITE = 0x00000002` — para escrita (rename, requer admin)
- PKEY_Device_FriendlyName: `fmtid={a45c254e-df1c-4efd-8020-67d146a850e0}`, `pid=14`
- Métodos usados: `GetValue(PROPVARIANT*)`, `SetValue(PROPVARIANT*)`

### IPolicyConfigClient
- `CLSID_PolicyConfigClient = "{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}"`
- IID (tentar em ordem, parar no primeiro que funcionar):
  1. `{ca286fc3-91fd-42c3-8e9b-caafa66242e3}` — Win10/11
  2. `{568b9108-44bf-40b4-9006-86afe5b5a620}` — Win10 alternativo
  3. `{f8679f50-850a-41cf-9c72-430f290290c8}` — Win7/8
- Método usado: `SetDefaultEndpoint(pwstrDeviceId: LPCWSTR, eRole: ERole) -> HRESULT`
- `ERole`: `eConsole=0`, `eMultimedia=1`, `eCommunications=2`

**Nota sobre vtable de IPolicyConfigClient:** A definição `comtypes` exige vtable exata. No Win10/11 com IID `{ca286fc3...}`, a sequência é: `GetMixFormat`, `GetDeviceFormat`, `ResetDeviceFormat`, `SetDeviceFormat`, `GetProcessingPeriod`, `SetProcessingPeriod`, `GetShareMode`, `SetShareMode`, `GetPropertyValue`, `SetPropertyValue`, **`SetDefaultEndpoint`**, `SetEndpointVisibility` — ou seja, 10 métodos placeholder antes de `SetDefaultEndpoint` na lista `_methods_` do comtypes. Implementar tentativa dos 3 IIDs em sequência com `try/except comtypes.COMError`; usar o primeiro que instanciar sem erro.

---

## Alterações em arquivos existentes

### `vbcable_setup.py`

No final de `install()`, após `result.returncode == 0`:

```python
from virtual_device import rename_cable_output

def install(progress_callback=None) -> bool:
    # ... código existente ...
    if result.returncode == 0:
        if progress_callback:
            progress_callback('Configurando dispositivo de áudio...')
        rename_cable_output()  # falha silenciosa — retorna bool ignorado aqui
        return True
    return False
```

### `audio_engine.py`

Adicionar `_prev_default_id: str | None = None` no `__init__`. Modificar `start()` e `stop()`:

```python
import virtual_device

def start(self):
    if self._thread and self._thread.is_alive():
        return
    # Salva default atual e define MTK como padrão
    self._prev_default_id = virtual_device.get_default_capture_id()
    dev_id = virtual_device.find_device_id(virtual_device.MTK_DEVICE_NAME, capture=True)
    if dev_id:
        virtual_device.set_as_default_capture(dev_id)
    # ... resto do código existente ...

def stop(self):
    self._stop_event.set()
    if self._thread and self._thread.is_alive():
        self._thread.join(timeout=2.0)
    self._thread = None
    # Restaura default anterior
    if self._prev_default_id:
        virtual_device.set_as_default_capture(self._prev_default_id)
        self._prev_default_id = None
```

### `requirements.txt`

Adicionar linha:
```
comtypes>=1.4
```

### `build.spec`

Adicionar `comtypes` a `hiddenimports` se ainda não presente. `comtypes` funciona frozen no PyInstaller sem configuração extra para COM nativo.

---

## Tratamento de erros

| Cenário | Comportamento |
|---------|---------------|
| CABLE Output não encontrado no rename | `logging.warning`, retorna `False`, nenhum crash |
| rename falha (sem admin ou COM error) | `logging.warning`, retorna `False`, nenhum crash |
| MTK device não encontrado no set_default | `logging.warning`, retorna `False`, engine não inicia sem o device de áudio mesmo assim |
| IPolicyConfigClient COM error | `logging.warning`, retorna `False`, filtro funciona mas default não muda |
| restore_default com `prev_default_id=None` | no-op silencioso |

---

## Testes

Sem testes unitários para chamadas COM (requerem hardware de áudio real e estado do SO). Testar manualmente:

1. Fresh install → VB-Cable instala → device aparece como "MTK Noise Canceller" em Configurações > Som do Windows
2. Ligar filtro → "MTK Noise Canceller" vira mic padrão (verificar em Configurações > Som)
3. Desligar filtro → mic padrão anterior restaurado
4. Sair do app → mic padrão restaurado (stop() chamado pelo tray quit)
5. Discord → mic dropdown mostra "MTK Noise Canceller"
