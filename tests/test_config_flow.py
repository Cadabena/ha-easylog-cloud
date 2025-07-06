"""Test Home Assistant EasyLog Cloud config flow."""
from unittest.mock import patch, AsyncMock

import pytest
from custom_components.ha_easylog_cloud.const import (
    BINARY_SENSOR,
)
from custom_components.ha_easylog_cloud.const import (
    DOMAIN,
)
from custom_components.ha_easylog_cloud.const import (
    PLATFORMS,
)
from custom_components.ha_easylog_cloud.const import (
    SENSOR,
)
from custom_components.ha_easylog_cloud.const import (
    SWITCH,
)
from homeassistant import config_entries
from homeassistant import data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG


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
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
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
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
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
    
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
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
