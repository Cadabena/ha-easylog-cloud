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
    
    # Mock the API client authenticate method
    coordinator.api_client.authenticate = AsyncMock()
    coordinator.api_client._cookies = {"session": "test_session"}
    
    await coordinator.authenticate()
    
    assert coordinator._cookies == {"session": "test_session"}
    coordinator.api_client.authenticate.assert_called_once()


async def test_fetch_devices_page_method(hass, mock_session):
    """Test fetch_devices_page method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client fetch_devices_page method
    devices_html = "<html><body>Devices page content</body></html>"
    coordinator.api_client.fetch_devices_page = AsyncMock(return_value=devices_html)
    
    result = await coordinator.fetch_devices_page()
    
    assert result == devices_html
    coordinator.api_client.fetch_devices_page.assert_called_once()


def test_extract_devices_arr_from_html_method(hass, mock_session):
    """Test coordinator extract_devices_arr_from_html method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method
    coordinator.api_client._extract_devices_arr_from_html = MagicMock(return_value="new Device(1, 'test')")
    
    # Test successful extraction
    html_with_devices = """
    <script>
        var devicesArr = [
            new Device(1, 'test', 'EL-USB-TC', 'Test Device', 'AA:BB:CC:DD:EE:FF', ...)
        ];
    </script>
    """
    
    result = coordinator._extract_devices_arr_from_html(html_with_devices)
    assert result == "new Device(1, 'test')"
    coordinator.api_client._extract_devices_arr_from_html.assert_called_once_with(html_with_devices)


def test_extract_device_list_method_success(hass, mock_session):
    """Test coordinator extract_device_list method with success."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method
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
    coordinator.api_client._extract_device_list = MagicMock(return_value=[mock_device])
    coordinator.api_client.account_name = "test_user"
    
    devices_js = "new Device(1, 'test', 'EL-USB-TC', 'Test Device')"
    html = "<html><span id='username'>test_user</span></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    assert result[0] == mock_device
    assert coordinator.account_name == "test_user"
    coordinator.api_client._extract_device_list.assert_called_once_with(devices_js, html)


def test_extract_device_list_method_insufficient_fields(hass, mock_session):
    """Test coordinator extract_device_list method with insufficient fields."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method to return empty list
    coordinator.api_client._extract_device_list = MagicMock(return_value=[])
    
    devices_js = "new Device(1, 'test')"  # Not enough fields
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 0
    coordinator.api_client._extract_device_list.assert_called_once_with(devices_js, html)


def test_extract_device_list_method_parsing_error(hass, mock_session):
    """Test coordinator extract_device_list method with parsing error."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method to return empty list
    coordinator.api_client._extract_device_list = MagicMock(return_value=[])
    
    devices_js = "new Device('invalid_id', 'test', 'EL-USB-TC', 'Test Device')"  # Invalid ID
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 0
    coordinator.api_client._extract_device_list.assert_called_once_with(devices_js, html)


def test_extract_device_list_method_invalid_date(hass, mock_session):
    """Test coordinator extract_device_list method with invalid date."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method
    mock_device = {
        "id": 1,
        "name": "Test Device",
        "model": "EL-USB-TC",
        "MAC Address": {"value": "AA:BB:CC:DD:EE:FF", "unit": ""},
        "Firmware Version": {"value": "1.2.3", "unit": ""},
        "SSID": {"value": "MyWiFi", "unit": ""},
        "WiFi Signal": {"value": "-50", "unit": None},
        "Last Updated": {"value": None, "unit": ""},  # Invalid date results in None
    }
    coordinator.api_client._extract_device_list = MagicMock(return_value=[mock_device])
    
    devices_js = "new Device(1, 'test', 'EL-USB-TC', 'Test Device')"
    html = "<html></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    device = result[0]
    assert device["Last Updated"]["value"] is None
    coordinator.api_client._extract_device_list.assert_called_once_with(devices_js, html)


def test_extract_device_list_method_no_username(hass, mock_session):
    """Test coordinator extract_device_list method without username in HTML."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method
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
    coordinator.api_client._extract_device_list = MagicMock(return_value=[mock_device])
    coordinator.api_client.account_name = None  # No username found
    
    devices_js = "new Device(1, 'test', 'EL-USB-TC', 'Test Device')"
    html = "<html><body>No username span here</body></html>"
    
    result = coordinator._extract_device_list(devices_js, html)
    
    assert len(result) == 1
    assert coordinator.account_name is None
    coordinator.api_client._extract_device_list.assert_called_once_with(devices_js, html)


async def test_coordinator_with_session(hass, mock_session):
    """Test coordinator with session property."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client methods
    coordinator.api_client.authenticate = AsyncMock()
    coordinator.api_client._cookies = {"session": "test_session"}
    
    await coordinator.authenticate()
    
    assert coordinator._cookies == {"session": "test_session"}
    coordinator.api_client.authenticate.assert_called_once()


async def test_coordinator_fetch_devices_with_session(hass, mock_session):
    """Test coordinator fetch_devices_page with session property."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    
    # Mock the API client method
    devices_html = "<html><body>Devices page content</body></html>"
    coordinator.api_client.fetch_devices_page = AsyncMock(return_value=devices_html)
    
    # Set cookies
    coordinator._cookies = {"session": "test_session"}
    
    result = await coordinator.fetch_devices_page()
    
    assert result == devices_html
    coordinator.api_client.fetch_devices_page.assert_called_once() 