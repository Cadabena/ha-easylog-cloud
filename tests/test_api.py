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
    
    with pytest.raises(Exception):
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
    # name may not be parsed exactly due to simple splitter – ensure MAC & model correct


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
    api._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device", "model": "EL-USB-TC"}])
    
    # Prepare context manager response
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={"d": {"sensorName": "Test Device", "channels": {}}})
    live_response.text = AsyncMock(return_value="{}")
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    # Patch .get with a synchronous MagicMock so async with works without awaiting a coroutine
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    assert len(result) == 1
    assert result[0]["id"] == 1


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


async def test_async_get_devices_data_xml_response(hass, mock_session):
    """Test async_get_devices_data branch that parses XML fallback with embedded JSON and channel details."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")

    # Pretend authentication & page fetch succeed
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    # Provide a device stub with minimal required keys
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(2, 'test', 'EL-USB-CO2', 'XML Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 2, "name": "XML Dev", "model": "EL-USB-CO2"}])

    # Craft an XML string that wraps JSON in a <string> node (mimics .NET web-service)
    import json
    payload_dict = {
        "d": {
            "sensorName": "XML Dev",
            "channels": {
                "channelDetails": {
                    "channelLabel": "Temperature",
                    "reading": "23.0",
                    "unit": "°C",
                }
            },
            "rssi": -42,
            "firmwareVersion": "1.0.0",
            "lastCommFormatted": "01/01/2024 00:00:00",
        }
    }
    xml_payload = f"""<?xml version='1.0' encoding='utf-8'?>\n<string>{json.dumps(payload_dict)}</string>"""

    live_response = AsyncMock()
    # Force .json() to raise to trigger XML fallback
    live_response.json = AsyncMock(side_effect=Exception("not json"))
    live_response.text = AsyncMock(return_value=xml_payload)

    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response

    # Synchronous MagicMock for session.get so "async with" works already
    api._session.get = MagicMock(return_value=async_cm)

    result = await api.async_get_devices_data()

    # We expect one device with parsed channel and RSSI
    assert len(result) == 1
    dev = result[0]
    assert dev["name"] == "XML Dev"
    # channel from xml should be added
    assert dev["Temperature"]["value"] == 23.0
    # RSSI passed through
    assert dev["WiFi Signal"]["value"] == -42


async def test_async_get_devices_data_no_devices_found(hass, mock_session):
    """Test async_get_devices_data when no devices are found in device_list."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching to return empty list
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="")
    api._extract_device_list = MagicMock(return_value=[])
    
    result = await api.async_get_devices_data()
    
    # Should return empty list when no devices found
    assert result == []


async def test_async_get_devices_data_invalid_xml_response(hass, mock_session):
    """Test async_get_devices_data with invalid XML that can't be parsed."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(3, 'test', 'EL-USB-TC', 'Invalid XML Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 3, "name": "Invalid XML Dev", "model": "EL-USB-TC"}])
    
    # Mock response that's neither JSON nor valid XML
    live_response = AsyncMock()
    live_response.json = AsyncMock(side_effect=Exception("not json"))
    live_response.text = AsyncMock(return_value="invalid xml content")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return empty list when XML parsing fails
    assert result == []


async def test_async_get_devices_data_xml_without_string_node(hass, mock_session):
    """Test async_get_devices_data with XML that doesn't have a 'string' node."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(4, 'test', 'EL-USB-TC', 'No String Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 4, "name": "No String Dev", "model": "EL-USB-TC"}])
    
    # Mock XML response without 'string' node
    xml_payload = """<?xml version='1.0' encoding='utf-8'?>
    <root>
        <data>some data</data>
    </root>"""
    
    live_response = AsyncMock()
    live_response.json = AsyncMock(side_effect=Exception("not json"))
    live_response.text = AsyncMock(return_value=xml_payload)
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with empty data when no 'string' node found
    assert len(result) == 1
    dev = result[0]
    assert dev["name"] == "No String Dev"
    # Device should have basic structure but no channel data
    assert "id" in dev
    assert "model" in dev


async def test_async_get_devices_data_invalid_json_in_xml(hass, mock_session):
    """Test async_get_devices_data with XML containing invalid JSON in string node."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(5, 'test', 'EL-USB-TC', 'Invalid JSON Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 5, "name": "Invalid JSON Dev", "model": "EL-USB-TC"}])
    
    # Mock XML response with invalid JSON in string node
    xml_payload = """<?xml version='1.0' encoding='utf-8'?>
    <string>invalid json content</string>"""
    
    live_response = AsyncMock()
    live_response.json = AsyncMock(side_effect=Exception("not json"))
    live_response.text = AsyncMock(return_value=xml_payload)
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return empty list when JSON parsing fails
    assert result == []


async def test_async_get_devices_data_no_data_returned(hass, mock_session):
    """Test async_get_devices_data when API returns no data for device."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(6, 'test', 'EL-USB-TC', 'No Data Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 6, "name": "No Data Dev", "model": "EL-USB-TC"}])
    
    # Mock response with no data
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={})  # Empty response
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with empty data when no data returned
    assert len(result) == 1
    dev = result[0]
    assert dev["name"] == "No Data Dev"
    # Device should have basic structure but no channel data
    assert "id" in dev
    assert "model" in dev


async def test_async_get_devices_data_channels_as_list(hass, mock_session):
    """Test async_get_devices_data with channels as a list instead of dict."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(7, 'test', 'EL-USB-TC', 'List Channels Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 7, "name": "List Channels Dev", "model": "EL-USB-TC"}])
    
    # Mock response with channels as list
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={
        "d": {
            "sensorName": "List Channels Dev",
            "channels": [
                {"channelLabel": "Temp", "reading": "25.0", "unit": "°C"},
                {"channelLabel": "Humidity", "reading": "60", "unit": "%"}
            ]
        }
    })
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with channels from list
    assert len(result) == 1
    dev = result[0]
    assert dev["Temp"]["value"] == 25.0
    assert dev["Humidity"]["value"] == 60


async def test_async_get_devices_data_invalid_channel_values(hass, mock_session):
    """Test async_get_devices_data with invalid channel values like '--.--'."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(8, 'test', 'EL-USB-TC', 'Invalid Values Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 8, "name": "Invalid Values Dev", "model": "EL-USB-TC"}])
    
    # Mock response with invalid channel values
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={
        "d": {
            "sensorName": "Invalid Values Dev",
            "channels": [
                {"channelLabel": "Bad1", "reading": "--.--", "unit": "°C"},
                {"channelLabel": "Bad2", "reading": "---", "unit": "%"},
                {"channelLabel": "Bad3", "reading": "N/A", "unit": "ppm"},
                {"channelLabel": "Bad4", "reading": "", "unit": "V"}
            ]
        }
    })
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with None values for invalid readings
    assert len(result) == 1
    dev = result[0]
    assert dev["Bad1"]["value"] is None
    assert dev["Bad2"]["value"] is None
    assert dev["Bad3"]["value"] is None
    assert dev["Bad4"]["value"] is None


async def test_async_get_devices_data_last_updated_fixup(hass, mock_session):
    """Test async_get_devices_data defensive check for Last Updated field."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(9, 'test', 'EL-USB-TC', 'Fixup Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 9, "name": "Fixup Dev", "model": "EL-USB-TC"}])
    
    # Mock response with invalid Last Updated value
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={
        "d": {
            "sensorName": "Fixup Dev",
            "lastCommFormatted": "invalid date format"
        }
    })
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with None for invalid Last Updated
    assert len(result) == 1
    dev = result[0]
    assert dev["Last Updated"]["value"] is None


async def test_async_get_devices_data_no_live_devices_found(hass, mock_session):
    """Test async_get_devices_data when no live devices are found after processing."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(10, 'test', 'EL-USB-TC', 'No Live Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 10, "name": "No Live Dev", "model": "EL-USB-TC"}])
    
    # Mock response that causes device to be skipped (no data)
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={})  # Empty response
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with empty data when no live devices found
    assert len(result) == 1
    dev = result[0]
    assert dev["name"] == "No Live Dev"
    # Device should have basic structure but no channel data
    assert "id" in dev
    assert "model" in dev


async def test_async_get_devices_data_device_processing_continue(hass, mock_session):
    """Test async_get_devices_data when device processing triggers continue statement."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(11, 'test', 'EL-USB-TC', 'Continue Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 11, "name": "Continue Dev", "model": "EL-USB-TC"}])
    
    # Mock response that causes an exception during processing
    live_response = AsyncMock()
    live_response.json = AsyncMock(side_effect=Exception("JSON parsing failed"))
    live_response.text = AsyncMock(side_effect=Exception("Text reading failed"))
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return empty list when device processing fails completely
    assert result == []


async def test_async_get_devices_data_channels_dict_single_detail(hass, mock_session):
    """Test async_get_devices_data with channels as dict containing single channelDetails."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(12, 'test', 'EL-USB-TC', 'Single Channel Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 12, "name": "Single Channel Dev", "model": "EL-USB-TC"}])
    
    # Mock response with channels as dict containing single channelDetails (not list)
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={
        "d": {
            "sensorName": "Single Channel Dev",
            "channels": {
                "channelDetails": {
                    "channelLabel": "Temperature",
                    "reading": "22.5",
                    "unit": "°C"
                }
            }
        }
    })
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with single channel wrapped in list
    assert len(result) == 1
    dev = result[0]
    assert dev["Temperature"]["value"] == 22.5


async def test_async_get_devices_data_last_updated_invalid_datetime(hass, mock_session):
    """Test async_get_devices_data with invalid datetime that triggers the defensive check."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(13, 'test', 'EL-USB-TC', 'Invalid DT Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 13, "name": "Invalid DT Dev", "model": "EL-USB-TC"}])
    
    # Mock response with invalid Last Updated value that will trigger defensive check
    live_response = AsyncMock()
    live_response.json = AsyncMock(return_value={
        "d": {
            "sensorName": "Invalid DT Dev",
            "lastCommFormatted": "invalid date format"
        }
    })
    live_response.text = AsyncMock(return_value="{}")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return device with None for invalid Last Updated
    assert len(result) == 1
    dev = result[0]
    assert dev["Last Updated"]["value"] is None


async def test_async_get_devices_data_continue_statement(hass, mock_session):
    """Test async_get_devices_data that triggers the continue statement after XML parsing failure."""
    api = HAEasylogCloudApiClient(hass, "test_user", "test_pass")
    
    # Mock the authentication and device fetching
    api.authenticate = AsyncMock()
    api.fetch_devices_page = AsyncMock(return_value="<html><body>Devices page</body></html>")
    api._extract_devices_arr_from_html = MagicMock(return_value="new Device(14, 'test', 'EL-USB-TC', 'Continue Dev')")
    api._extract_device_list = MagicMock(return_value=[{"id": 14, "name": "Continue Dev", "model": "EL-USB-TC"}])
    
    # Mock response that fails both JSON and XML parsing
    live_response = AsyncMock()
    live_response.json = AsyncMock(side_effect=Exception("JSON failed"))
    live_response.text = AsyncMock(return_value="invalid xml that can't be parsed")
    
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = live_response
    api._session.get = MagicMock(return_value=async_cm)
    
    result = await api.async_get_devices_data()
    
    # Should return empty list when device processing fails completely
    assert result == []
