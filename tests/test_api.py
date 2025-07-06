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


@pytest.fixture
def mock_session():
    """Create a mock session that doesn't trigger aiohttp warnings."""
    with patch('custom_components.ha_easylog_cloud.api.async_get_clientsession') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        yield mock_session


async def test_api_client_initialization(hass, mock_session):
    """Test API client initialization."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    assert api._username == "test_user"
    assert api._password == "test_pass"
    assert api._session is not None


async def test_authenticate_success(hass, mock_session):
    """Test successful authentication."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the login page response
    login_html = """
    <html>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__VIEWSTATEGENERATOR" value="test_viewstategen" />
    </html>
    """
    
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=login_html)
    mock_response.cookies = {"session": "test_session"}
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    await api.authenticate()
    
    assert api._cookies is not None
    assert mock_session.get.called
    assert mock_session.post.called


async def test_authenticate_missing_viewstate(hass, mock_session):
    """Test authentication with missing viewstate."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the login page response without viewstate
    login_html = "<html><body>No viewstate here</body></html>"
    
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=login_html)
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    with pytest.raises(KeyError):
        await api.authenticate()


async def test_fetch_devices_page(hass, mock_session):
    """Test fetch_devices_page method."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the devices page response
    devices_html = "<html><body>Devices page content</body></html>"
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=devices_html)
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    # Set cookies
    api._cookies = {"session": "test_session"}
    
    result = await api.fetch_devices_page()
    
    assert result == devices_html
    assert mock_session.get.called


def test_extract_devices_arr_from_html(hass, mock_session):
    """Test extract_devices_arr_from_html method."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
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


def test_extract_device_list_success(hass, mock_session):
    """Test extract_device_list method with success."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock devices JS with proper device data that matches the regex pattern
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
               '01/01/2024 12:00:00', [new Channel('Temperature', '25.5', '°C'), new Channel('Humidity', '60', '%')])
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


def test_extract_device_list_insufficient_fields(hass, mock_session):
    """Test extract_device_list method with insufficient fields."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock devices JS with insufficient fields
    devices_js = "new Device(1, 'test')"  # Not enough fields
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_parsing_error(hass, mock_session):
    """Test extract_device_list method with parsing error."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock devices JS with invalid data
    devices_js = "new Device('invalid_id', 'test', 'EL-USB-TC', 'Test Device')"  # Invalid ID
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_invalid_date(hass, mock_session):
    """Test extract_device_list method with invalid date."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
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
               'invalid_date', [new Channel('Temperature', '25.5', '°C'), new Channel('Humidity', '60', '%')])
    """
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["Last Updated"]["value"] is None


def test_extract_device_list_no_username(hass, mock_session):
    """Test extract_device_list method without username in HTML."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
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
               '01/01/2024 12:00:00', [new Channel('Temperature', '25.5', '°C'), new Channel('Humidity', '60', '%')])
    """
    
    html = "<html><body>No username span here</body></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    assert api.account_name is None


async def test_async_get_devices_data_success(hass, mock_session):
    """Test async_get_devices_data method with success."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(1, 'test', 'EL-USB-TC', 'Test Device')")
    api._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
    
    result = await api.async_get_devices_data()
    
    assert result == [{"id": 1, "name": "Test Device"}]
    api.authenticate.assert_called_once()
    api.fetch_devices_page.assert_called_once()


async def test_async_get_devices_data_authentication_failure(hass, mock_session):
    """Test async_get_devices_data method with authentication failure."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication to fail
    api.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
    
    with pytest.raises(Exception):
        await api.async_get_devices_data()


async def test_async_get_devices_data_no_devices(hass, mock_session):
    """Test async_get_devices_data method with no devices found."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>No devices</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="")
    api._extract_device_list = MagicMock(return_value=[])
    
    result = await api.async_get_devices_data()
    
    assert result == []
    api.authenticate.assert_called_once()
    api.fetch_devices_page.assert_called_once()


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
                    
                    assert len(result) == 0  # Device is not added when API fails


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


async def test_async_set_title(hass):
    """Test async_set_title stub method."""
    api = HAEasylogCloudApiClient(hass, "test", "test")
    
    result = await api.async_set_title("test_title")
    
    assert result is None


async def test_api_wrapper(hass):
    """Test api_wrapper stub method."""
    api = HAEasylogCloudApiClient(hass, "test", "test")
    
    result = await api.api_wrapper("get", "https://example.com")
    
    assert result is None
