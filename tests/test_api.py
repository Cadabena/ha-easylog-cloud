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
    """Mock aiohttp session used by the API client."""
    with patch('custom_components.ha_easylog_cloud.api.async_get_clientsession') as mock_get_session:
        session = AsyncMock()
        mock_get_session.return_value = session
        yield session


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
    
    # Configure session methods for awaitable calls (no context manager required here)
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=login_html)
    session = mock_session  # alias for clarity
    session.get = AsyncMock(return_value=mock_response)
    session.post = AsyncMock(return_value=mock_response)
    
    await api.authenticate()
    
    # Verify the authentication process
    session.get.assert_called_once()
    session.post.assert_called_once()


async def test_authenticate_missing_viewstate(hass, mock_session):
    """Test authentication with missing viewstate."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the login page response without viewstate
    login_html = "<html><body>No viewstate here</body></html>"
    
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=login_html)
    
    mock_session.get = AsyncMock(return_value=mock_response)
    
    with pytest.raises(KeyError):
        await api.authenticate()


async def test_fetch_devices_page(hass, mock_session):
    """Test fetch_devices_page method."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the devices page response
    devices_html = "<html><body>Devices page content</body></html>"
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=devices_html)
    
    session = mock_session
    session.get = AsyncMock(return_value=mock_response)
    
    # Set cookies
    api._cookies = {"session": "test_session"}
    
    result = await api.fetch_devices_page()
    
    assert result == devices_html


def test_extract_devices_arr_from_html(hass, mock_session):
    """Test _extract_devices_arr_from_html method."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock HTML with devices array
    html = """
    <html>
        <script>
            var devicesArr = [
                new Device(1, 'test', 'EL-USB-TC', 'Test Device')
            ];
        </script>
    </html>
    """
    
    result = api._extract_devices_arr_from_html(html)
    
    assert "new Device(1, 'test', 'EL-USB-TC', 'Test Device')" in result


def test_extract_device_list_success(hass, mock_session):
    """Test extract_device_list method with success."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock devices JS with proper device data that matches the actual regex pattern
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
    assert result[0]["id"] == 1
    assert result[0]["name"] == "Test Device"
    assert result[0]["model"] == "EL-USB-TC"
    assert result[0]["MAC Address"]["value"] == "AA:BB:CC:DD:EE:FF"


def test_extract_device_list_insufficient_fields(hass, mock_session):
    """Test extract_device_list method with insufficient fields."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock devices JS with insufficient fields
    devices_js = "new Device(1, 'test')"
    
    html = "<html></html>"
    
    result = api._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_parsing_error(hass, mock_session):
    """Test extract_device_list method with parsing error."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock devices JS with invalid format
    devices_js = "invalid javascript"
    
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
    assert result[0]["Last Updated"]["value"] is None


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
    assert api.account_name is None  # No username found in HTML


async def test_async_get_devices_data_success(hass, mock_session):
    """Test async_get_devices_data method with success."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(1, 'test', 'EL-USB-TC', 'Test Device')")
    api._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
    
    # Prepare context manager response
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={"d": {"sensorName": "Test Device", "channels": {}}})
    live_response.text = AsyncMock(return_value="{}")
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = AsyncMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    assert result == [{"id": 1, "name": "Test Device"}]


async def test_async_get_devices_data_authentication_failure(hass, mock_session):
    """Test async_get_devices_data method with authentication failure."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication to fail
    api.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
    
    result = await api.async_get_devices_data()
    
    # Should return empty list on exception
    assert result == []


async def test_async_get_devices_data_api_failure(hass, mock_session):
    """Test async_get_devices_data method with API failure."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication to succeed but API call to fail
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(side_effect=Exception("API failed"))
    
    result = await api.async_get_devices_data()
    
    # Should return empty list on exception
    assert result == []


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
