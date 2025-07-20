"""Test Home Assistant EasyLog Cloud coordinator."""
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from custom_components.ha_easylog_cloud.coordinator import EasylogCloudCoordinator


@pytest.fixture
def mock_session():
    """Mock aiohttp session."""
    with patch(
        "custom_components.ha_easylog_cloud.api.async_get_clientsession"
    ) as mock:
        session = AsyncMock()
        mock.return_value = session
        yield session


async def test_coordinator_initialization(hass, mock_session):
    """Test coordinator initialization."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    assert coordinator.api_client is not None
    assert coordinator._cookies is None
    assert coordinator.account_name is None


async def test_async_update_data_success(hass, mock_session):
    """Test async_update_data with success."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock the API client to return device data
    mock_devices = [{"id": 1, "name": "Test Device"}]
    coordinator.api_client.async_get_devices_data = AsyncMock(return_value=mock_devices)

    result = await coordinator._async_update_data()

    assert result == mock_devices


async def test_async_update_data_exception(hass, mock_session):
    """Test async_update_data with exception."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock the API client to raise an exception
    coordinator.api_client.async_get_devices_data = AsyncMock(
        side_effect=Exception("Test error")
    )

    with pytest.raises(Exception):
        await coordinator._async_update_data()


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
    """Test _extract_devices_arr_from_html method."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

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

    result = coordinator.api_client._extract_devices_arr_from_html(html)

    assert "new Device(1, 'test', 'EL-USB-TC', 'Test Device')" in result


def test_extract_device_list_method_success(hass, mock_session):
    """Test _extract_device_list method with success."""
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

    html = """
    <html>
        <span id="username">test_user</span>
    </html>
    """

    result = coordinator.api_client._extract_device_list(devices_js, html)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert "MAC Address" in result[0]


def test_extract_device_list_method_insufficient_fields(hass, mock_session):
    """Test _extract_device_list method with insufficient fields."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock devices JS with insufficient fields
    devices_js = "new Device(1, 'test')"

    html = "<html></html>"

    result = coordinator.api_client._extract_device_list(devices_js, html)

    assert len(result) == 0


def test_extract_device_list_method_parsing_error(hass, mock_session):
    """Test _extract_device_list method with parsing error."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock devices JS with invalid format
    devices_js = "invalid javascript"

    html = "<html></html>"

    result = coordinator.api_client._extract_device_list(devices_js, html)

    assert len(result) == 0


def test_extract_device_list_method_invalid_date(hass, mock_session):
    """Test _extract_device_list method with invalid date."""
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

    result = coordinator.api_client._extract_device_list(devices_js, html)

    assert len(result) == 1
    assert result[0]["Last Updated"]["value"] is None


def test_extract_device_list_method_no_username(hass, mock_session):
    """Test _extract_device_list method without username in HTML."""
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

    result = coordinator.api_client._extract_device_list(devices_js, html)

    assert len(result) == 1
    assert coordinator.account_name is None


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


def test_coordinator_proxy_extract_device_list(hass, mock_session):
    """Ensure coordinator proxy method sets account_name and returns list."""
    coordinator = EasylogCloudCoordinator(hass, "u", "p")

    devices_js = "new Device(3, 't', 'EL-USB-TC', 'Proxy Device', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '01/01/2024 00:00:00', [new Channel('Temperature', '20', '°C')])"
    html = """<html><span id='username'>proxy_user</span></html>"""

    result = coordinator._extract_device_list(devices_js, html)
    assert len(result) == 1
    assert coordinator.account_name == "proxy_user"


def test_coordinator_extract_device_list_method(hass, mock_session):
    """Test coordinator's _extract_device_list method directly."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock the API client's _extract_device_list method
    coordinator.api_client._extract_device_list = MagicMock(
        return_value=[{"id": 1, "name": "Test Device", "model": "Test Model"}]
    )
    coordinator.api_client.account_name = "test_user"

    # Call the coordinator's method directly
    result = coordinator._extract_device_list("test_js", "test_html")

    # Should return the device list and set account_name
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert coordinator.account_name == "test_user"


async def test_extract_device_list_returns_devices(hass, mock_session):
    """Test that _extract_device_list returns devices and sets account_name."""
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

    html = """
    <html>
        <span id="username">test_user</span>
    </html>
    """

    result = coordinator._extract_device_list(devices_js, html)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert coordinator.account_name == "test_user"


async def test_async_update_data_exception_handling(hass, mock_session):
    """Test _async_update_data exception handling (line 46)."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock the API client to raise an exception during data fetching
    coordinator.api_client.async_get_devices_data = AsyncMock(
        side_effect=Exception("API error")
    )

    # The exception should be caught and re-raised by the coordinator
    with pytest.raises(Exception, match="API error"):
        await coordinator._async_update_data()


async def test_async_update_data_exception_handling_specific(hass, mock_session):
    """Test _async_update_data exception handling specifically for line 46."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock the API client to raise a specific exception during data fetching
    coordinator.api_client.async_get_devices_data = AsyncMock(
        side_effect=ValueError("Specific API error")
    )

    # The exception should be caught and re-raised by the coordinator
    with pytest.raises(ValueError, match="Specific API error"):
        await coordinator._async_update_data()


async def test_async_update_data_exception_handling_line_46(hass, mock_session):
    """Test _async_update_data exception handling specifically for line 46."""
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")

    # Mock the API client to raise an exception during data fetching
    coordinator.api_client.async_get_devices_data = AsyncMock(
        side_effect=Exception("API error for line 46")
    )

    # The exception should be caught and re-raised by the coordinator
    with pytest.raises(Exception, match="API error for line 46"):
        await coordinator._async_update_data()
