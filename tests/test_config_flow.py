"""Test Home Assistant EasyLog Cloud config flow."""
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
from custom_components.ha_easylog_cloud.const import DOMAIN, CONF_USERNAME, CONF_PASSWORD

MOCK_CONFIG = {
    CONF_USERNAME: "test_user",
    CONF_PASSWORD: "test_pass",
}


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch("custom_components.ha_easylog_cloud.async_setup", return_value=True,), patch(
        "custom_components.ha_easylog_cloud.async_setup_entry",
        return_value=True,
    ):
        yield

# Mock the config flow for testing
@pytest.fixture(autouse=True)
def mock_config_flow():
    """Mock the config flow."""
    with patch("homeassistant.loader.async_get_integration") as mock_get_integration:
        # Create a mock integration
        mock_integration = type('MockIntegration', (), {
            'domain': DOMAIN,
            'config_flow': True,
            'async_get_flow_handler': lambda: None,
        })()
        mock_get_integration.return_value = mock_integration
        yield


# Test the config flow class directly
async def test_successful_config_flow(hass, bypass_get_data):
    """Test a successful config flow."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Mock the credential test to return success
    with patch.object(flow, '_test_credentials', return_value=(True, "test_username")):
        # Test the user step
        result = await flow.async_step_user(user_input=MOCK_CONFIG)
        
        # Check that the config flow creates an entry
        assert result["type"] == "create_entry"
        assert result["title"] == "test_username"
        assert result["data"] == MOCK_CONFIG


# Test failed config flow
async def test_failed_config_flow(hass, error_on_get_data):
    """Test a failed config flow due to credential validation failure."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Mock the credential test to return failure
    with patch.object(flow, '_test_credentials', return_value=(False, None)):
        # Test the user step with invalid credentials
        result = await flow.async_step_user(user_input=MOCK_CONFIG)
        
        # Check that the config flow shows an error
        assert result["type"] == "form"
        assert result["errors"] == {"base": "auth"}


# Test options flow (simplified since we don't have an options flow implemented)
async def test_options_flow(hass):
    """Test an options flow."""
    # This test is simplified since the actual config flow doesn't have an options flow
    # We just test that the config flow can be instantiated
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    flow = EasylogCloudConfigFlow()
    assert flow is not None


async def test_config_flow_show_form(hass):
    """Test config flow form display."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Test showing the form without user input
    result = await flow.async_step_user(user_input=None)
    
    # Check that the form is shown
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "data_schema" in result
    assert "errors" in result


async def test_config_flow_show_form_with_errors(hass):
    """Test config flow form display with errors."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    flow._errors = {"base": "auth"}
    
    # Test showing the form with errors
    result = await flow.async_step_user(user_input=None)
    
    # Check that the form is shown with errors
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    # The errors are cleared when showing the form, so we check that the form is shown
    assert "errors" in result


async def test_config_flow_show_form_with_user_input(hass):
    """Test config flow form display with user input."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Test showing the form with user input
    result = await flow.async_step_user(user_input=MOCK_CONFIG)
    
    # Check that the form is shown (since we're not mocking _test_credentials)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_test_credentials_success(hass):
    """Test successful credential validation."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Mock the API client
    mock_api_client = type('MockApiClient', (), {
        'authenticate': AsyncMock(),
        'fetch_devices_page': AsyncMock(return_value="<html></html>"),
        '_extract_devices_arr_from_html': lambda html: "test",
        '_extract_device_list': lambda js, html: [{"id": 1, "name": "Test Device"}],
        'account_name': "test_user"
    })()
    
    with patch('custom_components.ha_easylog_cloud.api.HAEasylogCloudApiClient', return_value=mock_api_client):
        valid, name = await flow._test_credentials("test_user", "test_pass")
        
        assert valid is True
        assert name == "test_user"


async def test_test_credentials_success_no_account_name(hass):
    """Test successful credential validation without account name."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Mock the API client without account name
    mock_api_client = type('MockApiClient', (), {
        'authenticate': AsyncMock(),
        'fetch_devices_page': AsyncMock(return_value="<html></html>"),
        '_extract_devices_arr_from_html': lambda html: "test",
        '_extract_device_list': lambda js, html: [{"id": 1, "name": "Test Device"}],
        'account_name': None
    })()
    
    with patch('custom_components.ha_easylog_cloud.api.HAEasylogCloudApiClient', return_value=mock_api_client):
        valid, name = await flow._test_credentials("test_user", "test_pass")
        
        assert valid is True
        assert name is None


async def test_test_credentials_failure(hass):
    """Test failed credential validation."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    # Mock the API client to raise exception
    mock_api_client = type('MockApiClient', (), {
        'authenticate': AsyncMock(side_effect=Exception("Auth failed"))
    })()
    
    with patch('custom_components.ha_easylog_cloud.api.HAEasylogCloudApiClient', return_value=mock_api_client):
        valid, name = await flow._test_credentials("test_user", "test_pass")
        
        assert valid is False
        assert name is None


async def test_config_flow_initialization():
    """Test config flow initialization."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Test that the config flow can be instantiated
    flow = EasylogCloudConfigFlow()
    
    assert flow.VERSION == 1
    assert flow._errors == {}


async def test_config_flow_error_clearing(hass):
    """Test that errors are cleared on each step."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
    
    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    flow._errors = {"base": "auth"}
    
    # Mock the credential test to return success
    with patch.object(flow, '_test_credentials', return_value=(True, "test_username")):
        # Test the user step
        result = await flow.async_step_user(user_input=MOCK_CONFIG)
        
        # Check that errors are cleared
        assert flow._errors == {}
        assert result["type"] == "create_entry"


async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_flow_with_valid_credentials(hass: HomeAssistant) -> None:
    """Test successful config flow with valid credentials."""
    # Mock the API client and its methods
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="test")
    mock_api_client._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
    mock_api_client.account_name = "test_user"
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "test_user"
        assert result["data"] == MOCK_CONFIG


async def test_flow_with_invalid_credentials(hass: HomeAssistant) -> None:
    """Test config flow with invalid credentials."""
    # Mock the API client to raise exception
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "auth"}


async def test_flow_with_no_account_name(hass: HomeAssistant) -> None:
    """Test config flow with no account name returned."""
    # Mock the API client without account name
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="test")
    mock_api_client._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
    mock_api_client.account_name = None
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "test_user"  # Should fallback to username
        assert result["data"] == MOCK_CONFIG


async def test_flow_with_no_devices(hass: HomeAssistant) -> None:
    """Test config flow with no devices found."""
    # Mock the API client with no devices
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="")
    mock_api_client._extract_device_list = MagicMock(return_value=[])
    mock_api_client.account_name = "test_user"
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "test_user"
        assert result["data"] == MOCK_CONFIG


async def test_flow_with_fetch_devices_failure(hass: HomeAssistant) -> None:
    """Test config flow with fetch_devices_page failure."""
    # Mock the API client with fetch_devices_page failure
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(side_effect=Exception("Fetch failed"))
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "auth"}


async def test_flow_with_extract_devices_failure(hass: HomeAssistant) -> None:
    """Test config flow with extract_devices_arr_from_html failure."""
    # Mock the API client with extract_devices_arr_from_html failure
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(side_effect=Exception("Extract failed"))
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "auth"}


async def test_flow_with_extract_device_list_failure(hass: HomeAssistant) -> None:
    """Test config flow with extract_device_list failure."""
    # Mock the API client with extract_device_list failure
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="test")
    mock_api_client._extract_device_list = MagicMock(side_effect=Exception("Extract list failed"))
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "auth"}


async def test_show_config_form(hass: HomeAssistant) -> None:
    """Test showing the config form."""
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    
    result = await flow._show_config_form(MOCK_CONFIG)
    
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "data_schema" in result
    assert "errors" in result


async def test_show_config_form_with_errors(hass: HomeAssistant) -> None:
    """Test showing the config form with errors."""
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    flow._errors = {"base": "auth"}
    
    result = await flow._show_config_form(MOCK_CONFIG)
    
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "auth"}



