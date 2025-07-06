"""Tests for Home Assistant EasyLog Cloud api."""
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

import aiohttp
import pytest
from bs4 import BeautifulSoup
import xmltodict

from custom_components.ha_easylog_cloud.api import (
    HAEasylogCloudApiClient,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def test_api_initialization(hass, aioclient_mock, caplog):
    """Test API client initialization."""

    # To test the api submodule, we first create an instance of our API client
    api = HAEasylogCloudApiClient(hass, "test", "test")

    # Test that the API client can be instantiated
    assert api._username == "test"
    assert api._password == "test"
    assert api._session is not None
    assert api._cookies is None
    assert api.account_name is None


async def test_authenticate_success(hass, aioclient_mock):
    """Test successful authentication."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the login page response
    login_html = """
    <html>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__VIEWSTATEGENERATOR" value="test_viewstategen" />
    </html>
    """
    
    aioclient_mock.get("https://www.easylogcloud.com/", text=login_html)
    aioclient_mock.post("https://www.easylogcloud.com/", status=200)
    
    await api.authenticate()
    
    assert api._cookies is not None
    assert len(aioclient_mock.mock_calls) == 2


async def test_authenticate_missing_viewstate(hass, aioclient_mock):
    """Test authentication with missing viewstate."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the login page response without viewstate
    login_html = "<html></html>"
    
    aioclient_mock.get("https://www.easylogcloud.com/", text=login_html)
    
    with pytest.raises(KeyError):
        await api.authenticate()


async def test_fetch_devices_page(hass, aioclient_mock):
    """Test fetching devices page."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the devices page response
    devices_html = "<html><body>Devices page content</body></html>"
    aioclient_mock.get("https://www.easylogcloud.com/devices.aspx", text=devices_html)
    
    # Set cookies
    api._cookies = {"session": "test_session"}
    
    result = await api.fetch_devices_page()
    
    assert result == devices_html
    assert len(aioclient_mock.mock_calls) == 1


def test_extract_devices_arr_from_html():
    """Test extracting devices array from HTML."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    # Test successful extraction
    html_with_devices = """
    <script>
        var devicesArr = [
            new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF', ...)
        ];
    </script>
    """
    
    result = api._extract_devices_arr_from_html(html_with_devices)
    assert "new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF'" in result
    
    # Test missing devices array
    html_without_devices = "<html><body>No devices here</body></html>"
    
    result = api._extract_devices_arr_from_html(html_without_devices)
    assert result == ""


def test_extract_device_list_success():
    """Test successful device list extraction."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    # Mock devices JS with proper device data
    devices_js = """
    new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF', 
               'test_location', 'test_group', 'test_notes', 'test_alerts', 
               'test_settings', 'test_calibration', 'test_maintenance', 
               'test_history', 'test_reports', 'test_export', 'test_import', 
               '1.2.3', 'MyWiFi', 'test_ip', 'test_port', 'test_protocol', 
               'test_encryption', 'test_authentication', 'test_authorization', 
               'test_permissions', 'test_roles', 'test_users', 'test_groups', 
               '-50', 'test_ssid', 'test_bssid', 'test_channel', 'test_frequency', 
               'test_bandwidth', 'test_security', 'test_password', 'test_psk', 
               '01/01/2024 12:00:00', [new Channel('Temperature', '25.5', '°C')])
    """
    
    html = """
    <html>
        <span id="username">test_user</span>
    </html>
    """
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["id"] == 1
    assert device["name"] == "Test Device"
    assert device["model"] == "EL-USB-TC"
    assert device["MAC Address"]["value"] == "AA:BB:CC:DD:EE:FF"
    assert device["Firmware Version"]["value"] == "1.2.3"
    assert device["SSID"]["value"] == "MyWiFi"
    assert device["WiFi Signal"]["value"] == "-50"
    assert api.account_name == "test_user"


def test_extract_device_list_insufficient_fields():
    """Test device list extraction with insufficient fields."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    # Mock devices JS with insufficient fields
    devices_js = "new Device(1, 'test')"  # Not enough fields
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_parsing_error():
    """Test device list extraction with parsing error."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    # Mock devices JS with invalid data
    devices_js = "new Device('invalid_id', 'test', 'EL-USB-TC', 'Test Device')"  # Invalid ID
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_invalid_date():
    """Test device list extraction with invalid date."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    # Mock devices JS with invalid date
    devices_js = """
    new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF', 
               'test_location', 'test_group', 'test_notes', 'test_alerts', 
               'test_settings', 'test_calibration', 'test_maintenance', 
               'test_history', 'test_reports', 'test_export', 'test_import', 
               '1.2.3', 'MyWiFi', 'test_ip', 'test_port', 'test_protocol', 
               'test_encryption', 'test_authentication', 'test_authorization', 
               'test_permissions', 'test_roles', 'test_users', 'test_groups', 
               '-50', 'test_ssid', 'test_bssid', 'test_channel', 'test_frequency', 
               'test_bandwidth', 'test_security', 'test_password', 'test_psk', 
               'invalid_date', [new Channel('Temperature', '25.5', '°C')])
    """
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["Last Updated"]["value"] is None


async def test_async_get_devices_data_success(hass, aioclient_mock):
    """Test successful device data retrieval."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
                "MAC Address": {"value": "AA:BB:CC:DD:EE:FF", "unit": ""},
                "Firmware Version": {"value": "1.2.3", "unit": ""},
                "SSID": {"value": "MyWiFi", "unit": ""},
                "WiFi Signal": {"value": "-50", "unit": None},
                "Last Updated": {"value": None, "unit": ""},
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock live data API response
                    live_data = {
                        "d": {
                            "sensorName": "Test Device",
                            "firmwareVersion": "1.2.3",
                            "rssi": "-50",
                            "lastCommFormatted": "01/01/2024 12:00:00",
                            "channels": {
                                "channelDetails": [
                                    {
                                        "channelLabel": "Temperature",
                                        "reading": "25.5",
                                        "unit": "°C"
                                    },
                                    {
                                        "channelLabel": "Humidity",
                                        "reading": "60",
                                        "unit": "%"
                                    }
                                ]
                            }
                        }
                    }
                    
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        json=live_data
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1
                    device = result[0]
                    assert device["id"] == 1
                    assert device["name"] == "Test Device"
                    assert device["Temperature"]["value"] == 25.5
                    assert device["Temperature"]["unit"] == "°C"
                    assert device["Humidity"]["value"] == 60
                    assert device["Humidity"]["unit"] == "%"


async def test_async_get_devices_data_xml_response(hass, aioclient_mock):
    """Test device data retrieval with XML response."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock XML response
                    xml_response = """
                    <string>{"d": {"sensorName": "Test Device", "channels": {"channelDetails": [{"channelLabel": "Temperature", "reading": "25.5", "unit": "°C"}]}}}</string>
                    """
                    
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        text=xml_response
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1
                    device = result[0]
                    assert device["Temperature"]["value"] == 25.5


async def test_async_get_devices_data_invalid_response(hass, aioclient_mock):
    """Test device data retrieval with invalid response."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock invalid response
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        text="invalid response"
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1  # Device is still added but without live data


async def test_async_get_devices_data_no_devices(hass, aioclient_mock):
    """Test device data retrieval with no devices."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction with no devices
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[]):
                    result = await api.async_get_devices_data()
                    
                    assert result == []


async def test_async_get_devices_data_exception(hass, aioclient_mock):
    """Test device data retrieval with exception."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication to raise exception
    with patch.object(api, 'authenticate', side_effect=Exception("Auth failed")):
        result = await api.async_get_devices_data()
        
        assert result == []


async def test_async_get_devices_data_invalid_values(hass, aioclient_mock):
    """Test device data retrieval with invalid values."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock response with invalid values
                    live_data = {
                        "d": {
                            "sensorName": "Test Device",
                            "channels": {
                                "channelDetails": [
                                    {
                                        "channelLabel": "Temperature",
                                        "reading": "--.--",  # Invalid value
                                        "unit": "°C"
                                    },
                                    {
                                        "channelLabel": "Humidity",
                                        "reading": "N/A",  # Invalid value
                                        "unit": "%"
                                    },
                                    {
                                        "channelLabel": "Pressure",
                                        "reading": "",  # Empty value
                                        "unit": "hPa"
                                    }
                                ]
                            }
                        }
                    }
                    
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        json=live_data
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1
                    device = result[0]
                    assert device["Temperature"]["value"] is None
                    assert device["Humidity"]["value"] is None
                    assert device["Pressure"]["value"] is None


async def test_async_get_devices_data_channels_list(hass, aioclient_mock):
    """Test device data retrieval with channels as list."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock response with channels as list
                    live_data = {
                        "d": {
                            "sensorName": "Test Device",
                            "channels": [
                                {
                                    "channelLabel": "Temperature",
                                    "reading": "25.5",
                                    "unit": "°C"
                                }
                            ]
                        }
                    }
                    
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        json=live_data
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1
                    device = result[0]
                    assert device["Temperature"]["value"] == 25.5


async def test_async_get_devices_data_single_channel(hass, aioclient_mock):
    """Test device data retrieval with single channel."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock response with single channel (not in list)
                    live_data = {
                        "d": {
                            "sensorName": "Test Device",
                            "channels": {
                                "channelDetails": {
                                    "channelLabel": "Temperature",
                                    "reading": "25.5",
                                    "unit": "°C"
                                }
                            }
                        }
                    }
                    
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        json=live_data
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1
                    device = result[0]
                    assert device["Temperature"]["value"] == 25.5


async def test_async_get_devices_data_no_channels(hass, aioclient_mock):
    """Test device data retrieval with no channels."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock authentication
    with patch.object(api, 'authenticate'):
        # Mock devices page
        with patch.object(api, 'fetch_devices_page', return_value="<html></html>"):
            # Mock device extraction
            mock_device = {
                "id": 1,
                "name": "Test Device",
                "model": "EL-USB-TC",
            }
            
            with patch.object(api, '_extract_devices_arr_from_html', return_value="test"):
                with patch.object(api, '_extract_device_list', return_value=[mock_device]):
                    # Mock response with no channels
                    live_data = {
                        "d": {
                            "sensorName": "Test Device"
                        }
                    }
                    
                    aioclient_mock.get(
                        "https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId=1",
                        json=live_data
                    )
                    
                    result = await api.async_get_devices_data()
                    
                    assert len(result) == 1
                    device = result[0]
                    # Should not have any channel data
                    assert "Temperature" not in device


async def test_async_set_title():
    """Test async_set_title stub method."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    result = await api.async_set_title("test_title")
    
    assert result is None


async def test_api_wrapper():
    """Test api_wrapper stub method."""
    api = HAEasylogCloudApiClient(None, "test", "test")
    
    result = await api.api_wrapper("get", "https://example.com")
    
    assert result is None
