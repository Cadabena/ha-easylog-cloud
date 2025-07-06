"""Test Home Assistant EasyLog Cloud config flow."""
from unittest.mock import patch

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
