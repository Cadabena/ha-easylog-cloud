"""Test Home Assistant EasyLog Cloud coordinator."""
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from datetime import datetime, timedelta
import aiohttp

from custom_components.ha_easylog_cloud.coordinator import EasylogCloudCoordinator
from custom_components.ha_easylog_cloud.const import DOMAIN
from .const import MOCK_CONFIG


@pytest.fixture
def mock_session():
    """Create a mock session that doesn't trigger aiohttp warnings."""
    with patch('custom_components.ha_easylog_cloud.coordinator.async_get_clientsession') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        yield mock_session


async def test_coordinator_initialization(hass, mock_session):
    """Test coordinator initialization."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    assert coordinator.api_client is not None
    assert coordinator._cookies is None
    assert coordinator.account_name is None


async def test_async_update_data_success(hass, mock_session):
    """Test successful async_update_data."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client response
    mock_data = {"devices": [{"id": 1, "name": "Test Device"}]}
    coordinator.api_client.async_get_devices_data = AsyncMock(return_value=mock_data)
    
    result = await coordinator._async_update_data()
    
    assert result == mock_data
    coordinator.api_client.async_get_devices_data.assert_called_once()


async def test_async_update_data_exception(hass, mock_session):
    """Test async_update_data with exception."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client to raise an exception
    coordinator.api_client.async_get_devices_data = AsyncMock(side_effect=Exception("Test error"))
    
    result = await coordinator._async_update_data()
    
    assert result is None


async def test_authenticate_method(hass, mock_session):
    """Test authenticate method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the session and response
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value="""
    <html>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__VIEWSTATEGENERATOR" value="test_viewstategen" />
    </html>
    """)
    mock_response.cookies = {"session": "test_session"}
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    await coordinator.authenticate()
    
    assert coordinator._cookies is not None
    assert mock_session.get.called
    assert mock_session.post.called


async def test_fetch_devices_page_method(hass, mock_session):
    """Test fetch_devices_page method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the session and response
    devices_html = "<html><body>Devices page content</body></html>"
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=devices_html)
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    # Set cookies
    coordinator._cookies = {"session": "test_session"}
    
    result = await coordinator.fetch_devices_page()
    
    assert result == devices_html
    assert mock_session.get.called


def test_extract_devices_arr_from_html_method(hass, mock_session):
    """Test coordinator extract_devices_arr_from_html method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Test successful extraction
    html_with_devices = """
    <script>
        var devicesArr = [
            new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF', ...)
        ];
    </script>
    """
    
    result = coordinator._extract_devices_arr_from_html(html_with_devices)
    assert "new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF'" in result
    
    # Test missing devices array
    html_without_devices = "<html><body>No devices here</body></html>"
    
    result = coordinator._extract_devices_arr_from_html(html_without_devices)
    assert result == ""


def test_extract_device_list_method_success(hass, mock_session):
    """Test coordinator extract_device_list method with success."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
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
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["id"] == 1
    assert device["name"] == "Test Device"
    assert device["model"] == "EL-USB-TC"
    assert device["MAC Address"]["value"] == "AA:BB:CC:DD:EE:FF"
    assert device["Firmware Version"]["value"] == "1.2.3"
    assert device["SSID"]["value"] == "MyWiFi"
    assert device["WiFi Signal"]["value"] == "-50"
    assert coordinator.account_name == "test_user"


def test_extract_device_list_method_insufficient_fields(hass, mock_session):
    """Test coordinator extract_device_list method with insufficient fields."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock devices JS with insufficient fields
    devices_js = "new Device(1, 'test')"  # Not enough fields
    
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_method_parsing_error(hass, mock_session):
    """Test coordinator extract_device_list method with parsing error."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock devices JS with invalid data
    devices_js = "new Device('invalid_id', 'test', 'EL-USB-TC', 'Test Device')"  # Invalid ID
    
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_method_invalid_date(hass, mock_session):
    """Test coordinator extract_device_list method with invalid date."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
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
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["Last Updated"]["value"] is None


def test_extract_device_list_method_no_username(hass, mock_session):
    """Test coordinator extract_device_list method without username in HTML."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
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
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    assert coordinator.account_name is None


async def test_coordinator_with_session(hass, mock_session):
    """Test coordinator with session property."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the login page response
    login_html = """
    <html>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__VIEWSTATEGENERATOR" value="test_viewstategen" />
    </html>
    """
    
    # Mock the response objects properly
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=login_html)
    mock_response.cookies = {"session": "test_session"}
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    await coordinator.authenticate()
    
    assert coordinator._cookies is not None
    assert mock_session.get.called
    assert mock_session.post.called


async def test_coordinator_fetch_devices_with_session(hass, mock_session):
    """Test coordinator fetch_devices_page with session property."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the devices page response
    devices_html = "<html><body>Devices page content</body></html>"
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=devices_html)
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    # Set cookies
    coordinator._cookies = {"session": "test_session"}
    
    result = await coordinator.fetch_devices_page()
    
    assert result == devices_html
    assert mock_session.get.called 