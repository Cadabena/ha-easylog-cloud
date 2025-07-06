"""Test Home Assistant EasyLog Cloud coordinator."""
from unittest.mock import patch, AsyncMock
import pytest
from datetime import datetime, timedelta

from custom_components.ha_easylog_cloud.coordinator import EasylogCloudCoordinator
from custom_components.ha_easylog_cloud.const import DOMAIN
from .const import MOCK_CONFIG


async def test_coordinator_initialization(hass):
    """Test coordinator initialization."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    assert coordinator.name == DOMAIN
    assert coordinator.update_interval == timedelta(minutes=1)
    assert coordinator.api_client is not None
    assert coordinator.api_client._username == "test_user"
    assert coordinator.api_client._password == "test_pass"
    assert coordinator._cookies is None
    assert coordinator.account_name is None


async def test_async_update_data_success(hass):
    """Test successful data update."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock API client response
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "EL-USB-TC",
        "Temperature": {"value": 25.5, "unit": "°C"}
    }]
    
    with patch.object(coordinator.api_client, 'async_get_devices_data', return_value=mock_data):
        result = await coordinator._async_update_data()
        
        assert result == mock_data


async def test_async_update_data_exception(hass):
    """Test data update with exception."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock API client to raise exception
    with patch.object(coordinator.api_client, 'async_get_devices_data', side_effect=Exception("API Error")):
        result = await coordinator._async_update_data()
        
        assert result is None


async def test_authenticate_method(hass, aioclient_mock):
    """Test coordinator authenticate method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the login page response
    login_html = """
    <html>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__VIEWSTATEGENERATOR" value="test_viewstategen" />
    </html>
    """
    
    aioclient_mock.get("https://www.easylogcloud.com/", text=login_html)
    aioclient_mock.post("https://www.easylogcloud.com/", status=200)
    
    await coordinator.authenticate()
    
    assert coordinator._cookies is not None
    assert len(aioclient_mock.mock_calls) == 2


async def test_fetch_devices_page_method(hass, aioclient_mock):
    """Test coordinator fetch_devices_page method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the devices page response
    devices_html = "<html><body>Devices page content</body></html>"
    aioclient_mock.get("https://www.easylogcloud.com/devices.aspx", text=devices_html)
    
    # Set cookies
    coordinator._cookies = {"session": "test_session"}
    
    result = await coordinator.fetch_devices_page()
    
    assert result == devices_html
    assert len(aioclient_mock.mock_calls) == 1


def test_extract_devices_arr_from_html_method():
    """Test coordinator extract_devices_arr_from_html method."""
    coordinator = EasylogCloudCoordinator(None, "test", "test")
    
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


def test_extract_device_list_method_success():
    """Test coordinator extract_device_list method with success."""
    coordinator = EasylogCloudCoordinator(None, "test", "test")
    
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


def test_extract_device_list_method_insufficient_fields():
    """Test coordinator extract_device_list method with insufficient fields."""
    coordinator = EasylogCloudCoordinator(None, "test", "test")
    
    # Mock devices JS with insufficient fields
    devices_js = "new Device(1, 'test')"  # Not enough fields
    
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_method_parsing_error():
    """Test coordinator extract_device_list method with parsing error."""
    coordinator = EasylogCloudCoordinator(None, "test", "test")
    
    # Mock devices JS with invalid data
    devices_js = "new Device('invalid_id', 'test', 'EL-USB-TC', 'Test Device')"  # Invalid ID
    
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 0


def test_extract_device_list_method_invalid_date():
    """Test coordinator extract_device_list method with invalid date."""
    coordinator = EasylogCloudCoordinator(None, "test", "test")
    
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
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["Last Updated"]["value"] is None


def test_extract_device_list_method_no_username():
    """Test coordinator extract_device_list method without username in HTML."""
    coordinator = EasylogCloudCoordinator(None, "test", "test")
    
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
    
    html = "<html><body>No username span here</body></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    assert coordinator.account_name is None


async def test_coordinator_with_session(hass, aioclient_mock):
    """Test coordinator with session property."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the session property
    mock_session = AsyncMock()
    coordinator._session = mock_session
    
    # Mock the login page response
    login_html = """
    <html>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__VIEWSTATEGENERATOR" value="test_viewstategen" />
    </html>
    """
    
    mock_session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value=login_html)
    mock_session.post.return_value.__aenter__.return_value.cookies = {"session": "test_session"}
    
    await coordinator.authenticate()
    
    assert coordinator._cookies is not None
    assert mock_session.get.called
    assert mock_session.post.called


async def test_coordinator_fetch_devices_with_session(hass, aioclient_mock):
    """Test coordinator fetch_devices_page with session property."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the session property
    mock_session = AsyncMock()
    coordinator._session = mock_session
    
    # Mock the devices page response
    devices_html = "<html><body>Devices page content</body></html>"
    mock_session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value=devices_html)
    
    # Set cookies
    coordinator._cookies = {"session": "test_session"}
    
    result = await coordinator.fetch_devices_page()
    
    assert result == devices_html
    assert mock_session.get.called 