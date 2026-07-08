import logging
from ctypes import (
    POINTER, Structure, Union, byref,
    c_uint, c_ushort, c_ulong, c_ulonglong, c_wchar_p, c_void_p, windll,
)
from ctypes.wintypes import BOOL, DWORD, LPWSTR

import struct
import winreg

import comtypes
import comtypes.client
from comtypes import CLSCTX_ALL, GUID, HRESULT, IUnknown, COMMETHOD

log = logging.getLogger(__name__)

MTK_DEVICE_NAME = "MTK Noise Canceller"
CABLE_OUTPUT_NAME = "CABLE Output"

_MM_DEVICES_CAPTURE = r'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture'
_PKEY_FRIENDLYNAME = '{a45c254e-df1c-4efd-8020-67d146a850e0},14'

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
        pv = store.GetValue(byref(PKEY_Device_FriendlyName))
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


def _propvariant_to_str(raw, regtype: int) -> str | None:
    if regtype == winreg.REG_SZ:
        return raw
    if regtype == winreg.REG_BINARY and len(raw) >= 10:
        vt = struct.unpack_from('<H', raw, 0)[0]
        if vt == VT_LPWSTR:
            try:
                return raw[8:].decode('utf-16-le').rstrip('\x00')
            except Exception:
                pass
    return None


def _str_to_propvariant(name: str, regtype: int):
    if regtype == winreg.REG_SZ:
        return name
    encoded = name.encode('utf-16-le') + b'\x00\x00'
    return struct.pack('<HHHH', VT_LPWSTR, 0, 0, 0) + encoded


def rename_cable_output(new_name: str = MTK_DEVICE_NAME) -> bool:
    """
    Rename the capture endpoint whose name contains CABLE_OUTPUT_NAME.
    Writes directly to HKLM MMDevices registry (requires admin).
    Returns True on success, False on any failure (logged as warning).
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _MM_DEVICES_CAPTURE) as root:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(root, i)
                except OSError:
                    break
                props_path = f'{_MM_DEVICES_CAPTURE}\\{guid}\\Properties'
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, props_path) as props:
                        try:
                            raw, regtype = winreg.QueryValueEx(props, _PKEY_FRIENDLYNAME)
                            current = _propvariant_to_str(raw, regtype)
                            if current and CABLE_OUTPUT_NAME in current:
                                with winreg.OpenKey(
                                    winreg.HKEY_LOCAL_MACHINE, props_path,
                                    0, winreg.KEY_SET_VALUE
                                ) as w:
                                    winreg.SetValueEx(
                                        w, _PKEY_FRIENDLYNAME, 0, regtype,
                                        _str_to_propvariant(new_name, regtype)
                                    )
                                log.info("Renamed audio device '%s' -> '%s'", current, new_name)
                                return True
                        except FileNotFoundError:
                            pass
                except OSError:
                    pass
                i += 1
        log.warning("rename_cable_output: device containing '%s' not found", CABLE_OUTPUT_NAME)
    except OSError as exc:
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
