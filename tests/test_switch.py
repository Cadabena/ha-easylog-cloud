"""Test Home Assistant EasyLog Cloud switch."""
from custom_components.ha_easylog_cloud.const import (
    DOMAIN,
)
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


async def test_switch_turn_on_off(hass):
    """Directly test EasylogCloudSwitch on/off helpers."""
    from custom_components.ha_easylog_cloud.switch import EasylogCloudSwitch

    # Dummy coordinator not used in logic
    mock_coordinator = type("MockCoordinator", (), {"async_write_ha_state": lambda self: None})()
    device = {"id": 42, "name": "Dev", "model": "Model", "Test Switch": {"value": "off"}}

    sw = EasylogCloudSwitch(mock_coordinator, device, "Test Switch", device["Test Switch"])
    # Monkeypatch the Entity helper to avoid needing a full HA instance
    sw.async_write_ha_state = lambda: None

    # Initially off
    assert sw.is_on is False

    # Turn on
    await sw.async_turn_on()
    assert sw.is_on is True

    # Turn off again
    await sw.async_turn_off()
    assert sw.is_on is False


def test_switch_device_info():
    """Test switch device_info property."""
    from custom_components.ha_easylog_cloud.switch import EasylogCloudSwitch
    
    # Create a mock coordinator
    mock_coordinator = type("MockCoordinator", (), {})()
    device = {"id": 42, "name": "Test Switch Device", "model": "Switch Model", "Test Switch": {"value": "off"}}
    
    sw = EasylogCloudSwitch(mock_coordinator, device, "Test Switch", device["Test Switch"])
    
    device_info = sw.device_info
    
    assert device_info["identifiers"] == {(DOMAIN, 42)}
    assert device_info["name"] == "Test Switch Device"
    assert device_info["manufacturer"] == "Lascar Electronics"
    assert device_info["model"] == "Switch Model"
