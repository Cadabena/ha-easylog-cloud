"""Test Home Assistant EasyLog Cloud switch."""
from unittest.mock import call
from unittest.mock import patch

from custom_components.ha_easylog_cloud import (
    async_setup_entry,
)
from custom_components.ha_easylog_cloud.const import (
    DEFAULT_NAME,
)
from custom_components.ha_easylog_cloud.const import (
    DOMAIN,
)
from custom_components.ha_easylog_cloud.const import (
    SWITCH,
)
from homeassistant.components.switch import SERVICE_TURN_OFF
from homeassistant.components.switch import SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG


async def test_switch_services(hass):
    """Test switch services."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    
    # Mock the coordinator data to include a switch
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
        "Test Switch": {"value": "off", "unit": ""}
    }]
    
    # Set up the entry with mocked data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = type('MockCoordinator', (), {
        'data': mock_data
    })()
    
    # Test that the switch setup works
    from custom_components.ha_easylog_cloud.switch import async_setup_entry
    await async_setup_entry(hass, config_entry, lambda entities: None)
