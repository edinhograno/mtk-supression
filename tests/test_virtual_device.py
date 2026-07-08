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
