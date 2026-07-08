# Virtual Device Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renomear "CABLE Output" para "MTK Noise Canceller" no sistema Windows e definir esse device como microfone padrão ao ligar o filtro, restaurando o anterior ao desligar.

**Architecture:** Novo módulo `virtual_device.py` encapsula toda lógica COM (Windows Core Audio API via `comtypes`). `vbcable_setup.install()` chama rename após instalação bem-sucedida (tem admin). `AudioEngine.start()/stop()` gerem o default capture device.

**Tech Stack:** Python 3.14, Windows 10/11 64-bit, `comtypes>=1.4`, Windows Core Audio API (IMMDeviceEnumerator, IPropertyStore, IPolicyConfigClient).

## Global Constraints

- Python 3.14, Windows 10/11 64-bit
- `comtypes>=1.4` adicionado ao `requirements.txt`
- `MTK_DEVICE_NAME = "MTK Noise Canceller"` e `CABLE_OUTPUT_NAME = "CABLE Output"` como constantes em `virtual_device.py`
- `rename_cable_output` usa `STGM_READWRITE` — requer admin; chamado apenas de `vbcable_setup.install()` (já tem UAC)
- `set_as_default_capture` usa `IPolicyConfigClient` — sem admin, por-usuário
- Fallback silencioso em todas funções: se falhar, loga `warning` e retorna `False`; app nunca crasha
- Device padrão anterior armazenado em `AudioEngine._prev_default_id: str | None` (memória, não config)
- Sem alteração em `main.py`, `config.py`, `settings_ui.py`, `first_run.py`, `tray.py`, `noise_filter.py`
- Interface pública de `AudioEngine` e `vbcable_setup.install()` não muda (assinaturas preservadas)
- PyInstaller onefile: `comtypes` funciona frozen sem configuração extra

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `virtual_device.py` | Criar | COM interfaces + find/rename/default |
| `requirements.txt` | Modificar | Adicionar `comtypes>=1.4` |
| `tests/test_virtual_device.py` | Criar | Testes unitários com mocks |
| `vbcable_setup.py` | Modificar | Chamar rename após install |
| `audio_engine.py` | Modificar | Set/restore default no start/stop |
| `build.spec` | Modificar | Adicionar comtypes a hiddenimports |
| `tests/test_vbcable_setup.py` | Modificar | Atualizar 1 test quebrado + adicionar test de rename |
| `tests/test_audio_engine.py` | Modificar | Adicionar tests de default device |

---

## Task 1: virtual_device.py + requirements.txt

**Files:**
- Create: `virtual_device.py`
- Modify: `requirements.txt`
- Create: `tests/test_virtual_device.py`

**Interfaces:**
- Produces:
  - `MTK_DEVICE_NAME: str = "MTK Noise Canceller"`
  - `CABLE_OUTPUT_NAME: str = "CABLE Output"`
  - `eCapture: int = 1`, `eConsole: int = 0`, `eMultimedia: int = 1`, `eCommunications: int = 2`
  - `find_device_id(name_fragment: str, capture: bool = True) -> str | None`
  - `get_default_capture_id() -> str | None`
  - `rename_cable_output(new_name: str = MTK_DEVICE_NAME) -> bool`
  - `set_as_default_capture(endpoint_id: str) -> bool`

- [ ] **Step 1: Write tests/test_virtual_device.py**

```python
import ctypes
import pytest
from unittest.mock import MagicMock, call


def test_module_exports():
    import virtual_device
    assert virtual_device.MTK_DEVICE_NAME == "MTK Noise Canceller"
    assert virtual_device.CABLE_OUTPUT_NAME == "CABLE Output"
    assert callable(virtual_device.find_device_id)
    assert callable(virtual_device.get_default_capture_id)
    assert callable(virtual_device.rename_cable_output)
    assert callable(virtual_device.set_as_default_capture)


def test_propvariant_is_16_bytes():
    from virtual_device import PROPVARIANT
    assert ctypes.sizeof(PROPVARIANT) == 16


def test_pkey_device_friendlyname_pid():
    from virtual_device import PKEY_Device_FriendlyName
    assert PKEY_Device_FriendlyName.pid == 14


def test_find_device_id_returns_none_when_no_devices(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_collection = MagicMock()
    mock_collection.GetCount.return_value = 0
    mock_enum = MagicMock()
    mock_enum.EnumAudioEndpoints.return_value = mock_collection
    mocker.patch("comtypes.client.CreateObject", return_value=mock_enum)

    assert virtual_device.find_device_id("MTK Noise Canceller") is None


def test_find_device_id_returns_id_on_match(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_device = MagicMock()
    mock_device.GetId.return_value = "endpoint-abc"
    mock_collection = MagicMock()
    mock_collection.GetCount.return_value = 1
    mock_collection.Item.return_value = mock_device
    mock_enum = MagicMock()
    mock_enum.EnumAudioEndpoints.return_value = mock_collection
    mocker.patch("comtypes.client.CreateObject", return_value=mock_enum)
    mocker.patch("virtual_device._get_friendly_name", return_value="MTK Noise Canceller")

    result = virtual_device.find_device_id("MTK Noise Canceller")
    assert result == "endpoint-abc"


def test_find_device_id_skips_non_matching(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_device = MagicMock()
    mock_collection = MagicMock()
    mock_collection.GetCount.return_value = 1
    mock_collection.Item.return_value = mock_device
    mock_enum = MagicMock()
    mock_enum.EnumAudioEndpoints.return_value = mock_collection
    mocker.patch("comtypes.client.CreateObject", return_value=mock_enum)
    mocker.patch("virtual_device._get_friendly_name", return_value="Realtek Microphone")

    assert virtual_device.find_device_id("MTK Noise Canceller") is None


def test_get_default_capture_id(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_device = MagicMock()
    mock_device.GetId.return_value = "default-id"
    mock_enum = MagicMock()
    mock_enum.GetDefaultAudioEndpoint.return_value = mock_device
    mocker.patch("comtypes.client.CreateObject", return_value=mock_enum)

    result = virtual_device.get_default_capture_id()
    assert result == "default-id"
    mock_enum.GetDefaultAudioEndpoint.assert_called_once_with(
        virtual_device.eCapture, virtual_device.eConsole
    )


def test_rename_cable_output_false_when_cable_absent(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_collection = MagicMock()
    mock_collection.GetCount.return_value = 0
    mock_enum = MagicMock()
    mock_enum.EnumAudioEndpoints.return_value = mock_collection
    mocker.patch("comtypes.client.CreateObject", return_value=mock_enum)

    assert virtual_device.rename_cable_output() is False


def test_rename_cable_output_calls_set_value_and_commit(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_store = MagicMock()
    mock_device = MagicMock()
    mock_device.OpenPropertyStore.return_value = mock_store
    mock_collection = MagicMock()
    mock_collection.GetCount.return_value = 1
    mock_collection.Item.return_value = mock_device
    mock_enum = MagicMock()
    mock_enum.EnumAudioEndpoints.return_value = mock_collection
    mocker.patch("comtypes.client.CreateObject", return_value=mock_enum)
    mocker.patch("virtual_device._get_friendly_name", return_value="CABLE Output")

    result = virtual_device.rename_cable_output()
    assert result is True
    mock_store.SetValue.assert_called_once()
    mock_store.Commit.assert_called_once()


def test_set_as_default_capture_sets_all_three_roles(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mock_pc = MagicMock()
    mocker.patch("comtypes.client.CreateObject", return_value=mock_pc)

    result = virtual_device.set_as_default_capture("ep-id")
    assert result is True
    assert mock_pc.SetDefaultEndpoint.call_count == 3
    mock_pc.SetDefaultEndpoint.assert_any_call("ep-id", virtual_device.eConsole)
    mock_pc.SetDefaultEndpoint.assert_any_call("ep-id", virtual_device.eMultimedia)
    mock_pc.SetDefaultEndpoint.assert_any_call("ep-id", virtual_device.eCommunications)


def test_set_as_default_capture_returns_false_when_no_policy_client(mocker):
    from importlib import reload
    import virtual_device
    reload(virtual_device)

    mocker.patch("virtual_device._create_policy_config", return_value=None)

    assert virtual_device.set_as_default_capture("ep-id") is False
```

- [ ] **Step 2: Run tests — expect all to fail**

```
cd c:\Git\mtk-noise-canceller
.venv\Scripts\python -m pytest tests/test_virtual_device.py -v
```

Expected: `ModuleNotFoundError: No module named 'virtual_device'` (ou similar)

- [ ] **Step 3: Add comtypes to requirements.txt**

Abrir `requirements.txt` e adicionar no final:
```
comtypes>=1.4
```

Instalar no venv:
```
.venv\Scripts\pip install comtypes>=1.4
```

- [ ] **Step 4: Create virtual_device.py**

```python
import logging
from ctypes import (
    POINTER, Structure, Union, byref,
    c_uint, c_ushort, c_ulong, c_ulonglong, c_wchar_p, c_void_p, windll,
)
from ctypes.wintypes import BOOL, DWORD, LPWSTR

import comtypes
import comtypes.client
from comtypes import CLSCTX_ALL, GUID, HRESULT, IUnknown, COMMETHOD

log = logging.getLogger(__name__)

MTK_DEVICE_NAME = "MTK Noise Canceller"
CABLE_OUTPUT_NAME = "CABLE Output"

# EDataFlow
eRender = 0
eCapture = 1

# ERole
eConsole = 0
eMultimedia = 1
eCommunications = 2

# STGM
STGM_READ = 0x00000000
STGM_READWRITE = 0x00000002

# Device state mask
DEVICE_STATE_ACTIVE = 0x00000001

# PROPVARIANT vt tag for wide string pointer
VT_LPWSTR = 31

# GUIDs
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
CLSID_PolicyConfigClient = GUID("{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}")


# ── Structs ──────────────────────────────────────────────────────────────────

class PROPERTYKEY(Structure):
    _fields_ = [("fmtid", GUID), ("pid", c_ulong)]


PKEY_Device_FriendlyName = PROPERTYKEY()
PKEY_Device_FriendlyName.fmtid = GUID("{a45c254e-df1c-4efd-8020-67d146a850e0}")
PKEY_Device_FriendlyName.pid = 14


class _PROPVARIANT_UNION(Union):
    _fields_ = [("pwszVal", c_wchar_p), ("_pad", c_ulonglong)]


class PROPVARIANT(Structure):
    _fields_ = [
        ("vt", c_ushort),
        ("wReserved1", c_ushort),
        ("wReserved2", c_ushort),
        ("wReserved3", c_ushort),
        ("_u", _PROPVARIANT_UNION),
    ]


# ── COM interfaces ────────────────────────────────────────────────────────────

class IPropertyStore(IUnknown):
    _iid_ = GUID("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetCount",
                  (["out"], POINTER(c_ulong), "cProps")),
        COMMETHOD([], HRESULT, "GetAt",
                  (["in"], c_ulong, "iProp"),
                  (["out"], POINTER(PROPERTYKEY), "pkey")),
        COMMETHOD([], HRESULT, "GetValue",
                  (["in"], POINTER(PROPERTYKEY), "key"),
                  (["out"], POINTER(PROPVARIANT), "pv")),
        COMMETHOD([], HRESULT, "SetValue",
                  (["in"], POINTER(PROPERTYKEY), "key"),
                  (["in"], POINTER(PROPVARIANT), "propvar")),
        COMMETHOD([], HRESULT, "Commit"),
    ]


class IMMDevice(IUnknown):
    _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
    _methods_ = [
        COMMETHOD([], HRESULT, "Activate",
                  (["in"], POINTER(GUID), "iid"),
                  (["in"], DWORD, "dwClsCtx"),
                  (["in"], c_void_p, "pActivationParams"),
                  (["out"], POINTER(POINTER(IUnknown)), "ppInterface")),
        COMMETHOD([], HRESULT, "OpenPropertyStore",
                  (["in"], DWORD, "stgmAccess"),
                  (["out"], POINTER(POINTER(IPropertyStore)), "ppProperties")),
        COMMETHOD([], HRESULT, "GetId",
                  (["out"], POINTER(LPWSTR), "ppstrId")),
        COMMETHOD([], HRESULT, "GetState",
                  (["out"], POINTER(DWORD), "pdwState")),
    ]


class IMMDeviceCollection(IUnknown):
    _iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC5392387B5E}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetCount",
                  (["out"], POINTER(c_uint), "pcDevices")),
        COMMETHOD([], HRESULT, "Item",
                  (["in"], c_uint, "nDevice"),
                  (["out"], POINTER(POINTER(IMMDevice)), "ppDevice")),
    ]


class IMMDeviceEnumerator(IUnknown):
    _iid_ = IID_IMMDeviceEnumerator
    _methods_ = [
        COMMETHOD([], HRESULT, "EnumAudioEndpoints",
                  (["in"], c_uint, "dataFlow"),
                  (["in"], DWORD, "dwStateMask"),
                  (["out"], POINTER(POINTER(IMMDeviceCollection)), "ppDevices")),
        COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint",
                  (["in"], c_uint, "dataFlow"),
                  (["in"], c_uint, "role"),
                  (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint")),
        COMMETHOD([], HRESULT, "GetDevice",
                  (["in"], LPWSTR, "pwstrId"),
                  (["out"], POINTER(POINTER(IMMDevice)), "ppDevice")),
        COMMETHOD([], HRESULT, "RegisterEndpointNotificationCallback",
                  (["in"], POINTER(IUnknown), "pClient")),
        COMMETHOD([], HRESULT, "UnregisterEndpointNotificationCallback",
                  (["in"], POINTER(IUnknown), "pClient")),
    ]


# IPolicyConfigClient — vtable identical across Win7-Win11; IID differs per OS
_POLICY_METHODS = [
    COMMETHOD([], HRESULT, "GetMixFormat",
              (["in"], LPWSTR), (["out"], c_void_p)),
    COMMETHOD([], HRESULT, "GetDeviceFormat",
              (["in"], LPWSTR), (["in"], BOOL), (["out"], c_void_p)),
    COMMETHOD([], HRESULT, "ResetDeviceFormat",
              (["in"], LPWSTR)),
    COMMETHOD([], HRESULT, "SetDeviceFormat",
              (["in"], LPWSTR), (["in"], c_void_p), (["in"], c_void_p)),
    COMMETHOD([], HRESULT, "GetProcessingPeriod",
              (["in"], LPWSTR), (["in"], BOOL), (["out"], c_void_p), (["out"], c_void_p)),
    COMMETHOD([], HRESULT, "SetProcessingPeriod",
              (["in"], LPWSTR), (["in"], c_void_p)),
    COMMETHOD([], HRESULT, "GetShareMode",
              (["in"], LPWSTR), (["out"], c_void_p)),
    COMMETHOD([], HRESULT, "SetShareMode",
              (["in"], LPWSTR), (["in"], c_void_p)),
    COMMETHOD([], HRESULT, "GetPropertyValue",
              (["in"], LPWSTR), (["in"], BOOL), (["in"], c_void_p), (["out"], c_void_p)),
    COMMETHOD([], HRESULT, "SetPropertyValue",
              (["in"], LPWSTR), (["in"], BOOL), (["in"], c_void_p), (["in"], c_void_p)),
    COMMETHOD([], HRESULT, "SetDefaultEndpoint",
              (["in"], LPWSTR, "pwstrDeviceId"),
              (["in"], c_uint, "eRole")),
    COMMETHOD([], HRESULT, "SetEndpointVisibility",
              (["in"], LPWSTR), (["in"], BOOL)),
]


class _IPolicyConfig_Win10(IUnknown):
    _iid_ = GUID("{ca286fc3-91fd-42c3-8e9b-caafa66242e3}")
    _methods_ = _POLICY_METHODS


class _IPolicyConfig_Alt(IUnknown):
    _iid_ = GUID("{568b9108-44bf-40b4-9006-86afe5b5a620}")
    _methods_ = _POLICY_METHODS


class _IPolicyConfig_Win7(IUnknown):
    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = _POLICY_METHODS


# ── Internal helpers ──────────────────────────────────────────────────────────

def _create_enumerator() -> IMMDeviceEnumerator:
    return comtypes.client.CreateObject(
        CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
    )


def _get_friendly_name(device: IMMDevice) -> str | None:
    try:
        store = device.OpenPropertyStore(STGM_READ)
        pv = PROPVARIANT()
        store.GetValue(byref(PKEY_Device_FriendlyName), byref(pv))
        if pv.vt == VT_LPWSTR and pv._u.pwszVal:
            name = pv._u.pwszVal
            windll.ole32.PropVariantClear(byref(pv))
            return name
    except comtypes.COMError:
        pass
    return None


def _create_policy_config():
    for cls in (_IPolicyConfig_Win10, _IPolicyConfig_Alt, _IPolicyConfig_Win7):
        try:
            return comtypes.client.CreateObject(CLSID_PolicyConfigClient, interface=cls)
        except comtypes.COMError:
            continue
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def find_device_id(name_fragment: str, capture: bool = True) -> str | None:
    """Return endpoint ID of first device whose FriendlyName contains name_fragment."""
    try:
        enum = _create_enumerator()
        flow = eCapture if capture else eRender
        collection = enum.EnumAudioEndpoints(flow, DEVICE_STATE_ACTIVE)
        count = collection.GetCount()
        for i in range(count):
            device = collection.Item(i)
            name = _get_friendly_name(device)
            if name and name_fragment in name:
                return device.GetId()
    except comtypes.COMError as exc:
        log.warning("find_device_id(%r) failed: %s", name_fragment, exc)
    return None


def get_default_capture_id() -> str | None:
    """Return endpoint ID of the current default capture device (eConsole)."""
    try:
        enum = _create_enumerator()
        device = enum.GetDefaultAudioEndpoint(eCapture, eConsole)
        return device.GetId()
    except comtypes.COMError as exc:
        log.warning("get_default_capture_id failed: %s", exc)
    return None


def rename_cable_output(new_name: str = MTK_DEVICE_NAME) -> bool:
    """
    Rename the capture endpoint whose name contains CABLE_OUTPUT_NAME.
    Requires admin (IPropertyStore STGM_READWRITE on HKLM-backed endpoint).
    Returns True on success, False on any failure (logged as warning).
    """
    try:
        enum = _create_enumerator()
        collection = enum.EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)
        count = collection.GetCount()
        for i in range(count):
            device = collection.Item(i)
            name = _get_friendly_name(device)
            if name and CABLE_OUTPUT_NAME in name:
                store = device.OpenPropertyStore(STGM_READWRITE)
                pv = PROPVARIANT()
                pv.vt = VT_LPWSTR
                pv._u.pwszVal = new_name
                store.SetValue(byref(PKEY_Device_FriendlyName), byref(pv))
                store.Commit()
                log.info("Renamed audio device '%s' -> '%s'", name, new_name)
                return True
        log.warning("rename_cable_output: device containing '%s' not found", CABLE_OUTPUT_NAME)
    except comtypes.COMError as exc:
        log.warning("rename_cable_output failed: %s", exc)
    return False


def set_as_default_capture(endpoint_id: str) -> bool:
    """
    Set endpoint_id as default capture for eConsole, eMultimedia, eCommunications.
    Uses IPolicyConfigClient (undocumented COM, no admin required, per-user).
    Returns True on success, False on any failure (logged as warning).
    """
    try:
        pc = _create_policy_config()
        if pc is None:
            log.warning("set_as_default_capture: IPolicyConfigClient unavailable on this system")
            return False
        for role in (eConsole, eMultimedia, eCommunications):
            pc.SetDefaultEndpoint(endpoint_id, role)
        return True
    except comtypes.COMError as exc:
        log.warning("set_as_default_capture(%r) failed: %s", endpoint_id, exc)
    return False
```

- [ ] **Step 5: Run tests — expect all to pass**

```
.venv\Scripts\python -m pytest tests/test_virtual_device.py -v
```

Expected output (11 tests):
```
PASSED tests/test_virtual_device.py::test_module_exports
PASSED tests/test_virtual_device.py::test_propvariant_is_16_bytes
PASSED tests/test_virtual_device.py::test_pkey_device_friendlyname_pid
PASSED tests/test_virtual_device.py::test_find_device_id_returns_none_when_no_devices
PASSED tests/test_virtual_device.py::test_find_device_id_returns_id_on_match
PASSED tests/test_virtual_device.py::test_find_device_id_skips_non_matching
PASSED tests/test_virtual_device.py::test_get_default_capture_id
PASSED tests/test_virtual_device.py::test_rename_cable_output_false_when_cable_absent
PASSED tests/test_virtual_device.py::test_rename_cable_output_calls_set_value_and_commit
PASSED tests/test_virtual_device.py::test_set_as_default_capture_sets_all_three_roles
PASSED tests/test_virtual_device.py::test_set_as_default_capture_returns_false_when_no_policy_client
11 passed
```

- [ ] **Step 6: Commit**

```bash
git add virtual_device.py requirements.txt tests/test_virtual_device.py
git commit -m "feat: add virtual_device module — rename CABLE Output and manage default capture"
```

---

## Task 2: Wire vbcable_setup.py + audio_engine.py + build.spec

**Files:**
- Modify: `vbcable_setup.py` (linhas 57–83 — função `install`)
- Modify: `audio_engine.py` (linhas 12–18 `__init__`, 28–33 `start`, 35–40 `stop`)
- Modify: `build.spec` (linha 21 — lista `hiddenimports`)
- Modify: `tests/test_vbcable_setup.py` (atualizar 1 teste + adicionar 2)
- Modify: `tests/test_audio_engine.py` (adicionar 3 testes)

**Interfaces:**
- Consumes de Task 1:
  - `virtual_device.MTK_DEVICE_NAME: str`
  - `virtual_device.find_device_id(name_fragment: str, capture: bool = True) -> str | None`
  - `virtual_device.get_default_capture_id() -> str | None`
  - `virtual_device.rename_cable_output(new_name: str = MTK_DEVICE_NAME) -> bool`
  - `virtual_device.set_as_default_capture(endpoint_id: str) -> bool`

- [ ] **Step 1: Rodar testes existentes para verificar baseline**

```
.venv\Scripts\python -m pytest tests/test_vbcable_setup.py tests/test_audio_engine.py -v
```

Expected: todos passam (6 + 5 = 11 testes).

- [ ] **Step 2: Adicionar testes em tests/test_vbcable_setup.py**

Adicionar no final do arquivo `tests/test_vbcable_setup.py`:

```python
def test_install_calls_rename_on_success(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=0)
    mock_rename = mocker.patch('virtual_device.rename_cable_output', return_value=True)

    vbcable_setup.install()

    mock_rename.assert_called_once()


def test_install_does_not_rename_on_failure(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=1)
    mock_rename = mocker.patch('virtual_device.rename_cable_output', return_value=True)

    vbcable_setup.install()

    mock_rename.assert_not_called()
```

- [ ] **Step 3: Adicionar testes em tests/test_audio_engine.py**

Adicionar no final do arquivo `tests/test_audio_engine.py`:

```python
def test_start_saves_prev_default_and_sets_mtk(mocker):
    mocker.patch('virtual_device.get_default_capture_id', return_value='prev-id')
    mocker.patch('virtual_device.find_device_id', return_value='mtk-id')
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    mocker.patch.object(e, '_run')  # prevent real audio thread
    e.start()
    e.stop()

    assert mock_set.call_args_list[0] == call('mtk-id')
    assert e._prev_default_id is None  # stop() cleared it


def test_stop_restores_previous_default(mocker):
    mocker.patch('virtual_device.get_default_capture_id', return_value='prev-id')
    mocker.patch('virtual_device.find_device_id', return_value='mtk-id')
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    mocker.patch.object(e, '_run')
    e.start()
    e.stop()

    # Last set_as_default_capture call must restore prev-id
    assert mock_set.call_args_list[-1] == call('prev-id')


def test_stop_without_start_does_not_restore(mocker):
    mock_set = mocker.patch('virtual_device.set_as_default_capture', return_value=True)

    from importlib import reload
    import audio_engine
    reload(audio_engine)
    e = audio_engine.AudioEngine()
    e.stop()

    mock_set.assert_not_called()
```

- [ ] **Step 4: Rodar novos testes — esperar falha**

```
.venv\Scripts\python -m pytest tests/test_vbcable_setup.py::test_install_calls_rename_on_success tests/test_vbcable_setup.py::test_install_does_not_rename_on_failure tests/test_audio_engine.py::test_start_saves_prev_default_and_sets_mtk tests/test_audio_engine.py::test_stop_restores_previous_default tests/test_audio_engine.py::test_stop_without_start_does_not_restore -v
```

Expected: 5 falhas (funções não existem ainda).

- [ ] **Step 5: Modificar vbcable_setup.py**

Adicionar import no topo do arquivo (após `import sounddevice as sd`):

```python
import virtual_device
```

Substituir a função `install` completa (linhas 57–83):

```python
def install(progress_callback=None) -> bool:
    installer = get_bundled_installer_path()

    if not os.path.exists(installer):
        try:
            installer = _download_installer(progress_callback)
        except Exception:
            return False

    if not os.path.exists(installer):
        return False

    if progress_callback:
        progress_callback('Instalando driver VB-Cable...')

    cwd = os.path.dirname(installer)
    ps_cmd = (
        f'$p = Start-Process -FilePath "{installer}" -ArgumentList "/S"'
        f' -Verb RunAs -Wait -WorkingDirectory "{cwd}" -PassThru;'
        f' exit $p.ExitCode'
    )
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', ps_cmd],
        capture_output=True,
        timeout=120,
    )
    if result.returncode == 0:
        if progress_callback:
            progress_callback('Configurando dispositivo de áudio...')
        virtual_device.rename_cable_output()
        return True
    return False
```

- [ ] **Step 6: Modificar audio_engine.py**

Adicionar import no topo do arquivo (após `from noise_filter import NoiseFilter`):

```python
import virtual_device
```

Substituir `__init__` completo (linhas 12–18):

```python
def __init__(self):
    self._filter = NoiseFilter()
    self._stop_event = threading.Event()
    self._thread = None
    self._input_device = None
    self._intensity = 0.75
    self._last_error = None
    self._prev_default_id: str | None = None
```

Substituir `start` completo (linhas 28–33):

```python
def start(self):
    if self._thread and self._thread.is_alive():
        return
    self._stop_event.clear()
    self._prev_default_id = virtual_device.get_default_capture_id()
    dev_id = virtual_device.find_device_id(virtual_device.MTK_DEVICE_NAME, capture=True)
    if dev_id:
        virtual_device.set_as_default_capture(dev_id)
    self._thread = threading.Thread(target=self._run, daemon=True)
    self._thread.start()
```

Substituir `stop` completo (linhas 35–40):

```python
def stop(self):
    self._stop_event.set()
    if self._thread and self._thread.is_alive():
        self._thread.join(timeout=2.0)
    self._thread = None
    if self._prev_default_id:
        virtual_device.set_as_default_capture(self._prev_default_id)
        self._prev_default_id = None
```

- [ ] **Step 7: Modificar build.spec — adicionar comtypes a hiddenimports**

Em `build.spec`, localizar a lista `hiddenimports` (linha 21) e adicionar `'comtypes'` e `'comtypes.client'`:

```python
    hiddenimports=[
        'comtypes',
        'comtypes.client',
        'pedalboard',
        'pedalboard.pedalboard',
        'pedalboard._pedalboard',
        'pedalboard.io',
        'sounddevice',
        'numpy',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.IcoImagePlugin',
        'queue',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
```

- [ ] **Step 8: Atualizar test_install_calls_progress_callback no test_vbcable_setup.py**

O teste existente `test_install_calls_progress_callback` agora falhará porque `install()` chama `progress_callback` 2 vezes (antes: 1 vez). Localizar o teste e atualizar a assertion:

```python
def test_install_calls_progress_callback(mocker, tmp_path):
    installer = tmp_path / 'VBCABLE_Setup_x64.exe'
    installer.write_bytes(b'fake')
    from importlib import reload
    import vbcable_setup
    reload(vbcable_setup)
    mocker.patch('vbcable_setup.get_bundled_installer_path', return_value=str(installer))
    mocker.patch('subprocess.run').return_value = MagicMock(returncode=0)
    mocker.patch('virtual_device.rename_cable_output', return_value=True)
    messages = []
    vbcable_setup.install(progress_callback=messages.append)
    assert len(messages) == 2
    assert any('VB-Cable' in m for m in messages)
    assert any('áudio' in m for m in messages)
```

- [ ] **Step 9: Rodar todos os testes**

```
.venv\Scripts\python -m pytest tests/test_virtual_device.py tests/test_vbcable_setup.py tests/test_audio_engine.py -v
```

Expected: todos passam (11 + 7 + 9 = 27 testes).

- [ ] **Step 10: Commit**

```bash
git add vbcable_setup.py audio_engine.py build.spec tests/test_vbcable_setup.py tests/test_audio_engine.py
git commit -m "feat: wire virtual device identity into vbcable_setup and audio_engine"
```

---

## Teste Manual (após build)

1. Build: `.venv\Scripts\python -m PyInstaller build.spec`
2. Run installer — verificar que "MTK Noise Canceller" aparece em Configurações > Som > Dispositivos de entrada
3. Ligar filtro na UI — verificar que "MTK Noise Canceller" vira mic padrão (ícone de check em Configurações > Som)
4. Discord: Configurações > Voz & Vídeo — "MTK Noise Canceller" deve aparecer no dropdown de microfone
5. Desligar filtro — verificar que o mic padrão anterior é restaurado
6. Fechar app (tray → Sair) — verificar que o mic padrão anterior é restaurado
