"""Test Home Assistant EasyLog Cloud binary sensor."""
from unittest.mock import patch
import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_easylog_cloud.const import DOMAIN
from .const import MOCK_CONFIG


async def test_binary_sensor_setup(hass):
    """Test binary sensor setup."""
    from custom_components.ha_easylog_cloud.binary_sensor import async_setup_entry
    
    # Create a mock entry
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    
    # Mock coordinator data with binary sensors
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
        "Motion": {"value": "true", "unit": ""},
        "Door Contact": {"value": "false", "unit": ""},
        "Window": {"value": "on", "unit": ""},
        "Battery": {"value": "1", "unit": ""},
        "Power": {"value": 0, "unit": ""},
        "Temperature": {"value": 25.5, "unit": "°C"},  # Non-binary sensor
        "Humidity": {"value": 60, "unit": "%"},  # Non-binary sensor
    }]
    
    # Set up the entry with mocked data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = type('MockCoordinator', (), {
        'data': mock_data
    })()
    
    # Track added entities
    added_entities = []
    
    def mock_add_entities(entities):
        added_entities.extend(entities)
    
    # Test setup
    await async_setup_entry(hass, config_entry, mock_add_entities)
    
    # Verify that only binary sensors were added
    assert len(added_entities) == 5  # Motion, Door Contact, Window, Battery, Power
    
    # Verify entity properties
    motion_sensor = next(e for e in added_entities if "Motion" in e.name)
    assert motion_sensor.name == "Test Device Motion"
    assert motion_sensor.unique_id == "1_motion"
    assert motion_sensor.device_class == BinarySensorDeviceClass.MOTION
    assert motion_sensor.is_on is True
    
    door_sensor = next(e for e in added_entities if "Door Contact" in e.name)
    assert door_sensor.name == "Test Device Door Contact"
    assert door_sensor.unique_id == "1_door_contact"
    assert door_sensor.device_class == BinarySensorDeviceClass.DOOR
    assert door_sensor.is_on is False
    
    window_sensor = next(e for e in added_entities if "Window" in e.name)
    assert window_sensor.name == "Test Device Window"
    assert window_sensor.unique_id == "1_window"
    assert window_sensor.device_class == BinarySensorDeviceClass.WINDOW
    assert window_sensor.is_on is True
    
    battery_sensor = next(e for e in added_entities if "Battery" in e.name)
    assert battery_sensor.name == "Test Device Battery"
    assert battery_sensor.unique_id == "1_battery"
    assert battery_sensor.device_class == BinarySensorDeviceClass.BATTERY
    assert battery_sensor.is_on is True
    
    power_sensor = next(e for e in added_entities if "Power" in e.name)
    assert power_sensor.name == "Test Device Power"
    assert power_sensor.unique_id == "1_power"
    assert power_sensor.device_class == BinarySensorDeviceClass.POWER
    assert power_sensor.is_on is False


def test_is_binary_function():
    """Test the _is_binary helper function."""
    from custom_components.ha_easylog_cloud.binary_sensor import _is_binary
    
    # Test string values
    assert _is_binary({"value": "true"}) is True
    assert _is_binary({"value": "false"}) is True
    assert _is_binary({"value": "on"}) is True
    assert _is_binary({"value": "off"}) is True
    assert _is_binary({"value": "1"}) is True
    assert _is_binary({"value": "0"}) is True
    
    # Test numeric values
    assert _is_binary({"value": 1}) is True
    assert _is_binary({"value": 0}) is True
    assert _is_binary({"value": 1.0}) is True
    assert _is_binary({"value": 0.0}) is True
    
    # Test non-binary values
    assert _is_binary({"value": "hello"}) is False
    assert _is_binary({"value": 25.5}) is False
    assert _is_binary({"value": 100}) is False
    assert _is_binary({"value": None}) is False
    assert _is_binary({"value": ""}) is False
    
    # Test edge cases
    assert _is_binary({}) is False
    assert _is_binary({"value": "TRUE"}) is True  # Case insensitive
    assert _is_binary({"value": "FALSE"}) is True  # Case insensitive


def test_is_binary_exception_handling():
    """Test _is_binary function with exception handling."""
    from custom_components.ha_easylog_cloud.binary_sensor import _is_binary
    
    # Test with data that causes exception when accessing .get()
    class MockData:
        def get(self, key):
            raise Exception("Test exception")
    
    # Should return False when exception occurs
    assert _is_binary(MockData()) is False


def test_device_class_guessing():
    """Test device class guessing logic."""
    from custom_components.ha_easylog_cloud.binary_sensor import EasylogCloudBinarySensor
    
    # Create a mock coordinator and device
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test motion detection
    motion_sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Motion Sensor", {"value": "true"})
    assert motion_sensor._attr_device_class == BinarySensorDeviceClass.MOTION
    
    # Test door detection
    door_sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Contact Sensor", {"value": "true"})
    assert door_sensor._attr_device_class == BinarySensorDeviceClass.DOOR
    
    # Test window detection
    window_sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Window Sensor", {"value": "true"})
    assert window_sensor._attr_device_class == BinarySensorDeviceClass.WINDOW
    
    # Test battery detection
    battery_sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Battery Status", {"value": "true"})
    assert battery_sensor._attr_device_class == BinarySensorDeviceClass.BATTERY
    
    # Test power detection
    power_sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Power Status", {"value": "true"})
    assert power_sensor._attr_device_class == BinarySensorDeviceClass.POWER
    
    # Test unknown sensor
    unknown_sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Unknown Sensor", {"value": "true"})
    assert unknown_sensor._attr_device_class is None


def test_binary_sensor_is_on_property():
    """Test the is_on property of binary sensors."""
    from custom_components.ha_easylog_cloud.binary_sensor import EasylogCloudBinarySensor
    
    # Create a mock coordinator
    mock_coordinator = type('MockCoordinator', (), {})()
    
    # Test string values
    mock_device_true = {"id": 1, "name": "Test Device", "Test": {"value": "true"}}
    sensor_true = EasylogCloudBinarySensor(mock_coordinator, mock_device_true, "Test", {"value": "true"})
    assert sensor_true.is_on is True
    
    mock_device_on = {"id": 1, "name": "Test Device", "Test": {"value": "on"}}
    sensor_on = EasylogCloudBinarySensor(mock_coordinator, mock_device_on, "Test", {"value": "on"})
    assert sensor_on.is_on is True
    
    mock_device_1 = {"id": 1, "name": "Test Device", "Test": {"value": "1"}}
    sensor_1 = EasylogCloudBinarySensor(mock_coordinator, mock_device_1, "Test", {"value": "1"})
    assert sensor_1.is_on is True
    
    mock_device_false = {"id": 1, "name": "Test Device", "Test": {"value": "false"}}
    sensor_false = EasylogCloudBinarySensor(mock_coordinator, mock_device_false, "Test", {"value": "false"})
    assert sensor_false.is_on is False
    
    mock_device_off = {"id": 1, "name": "Test Device", "Test": {"value": "off"}}
    sensor_off = EasylogCloudBinarySensor(mock_coordinator, mock_device_off, "Test", {"value": "off"})
    assert sensor_off.is_on is False
    
    mock_device_0 = {"id": 1, "name": "Test Device", "Test": {"value": "0"}}
    sensor_0 = EasylogCloudBinarySensor(mock_coordinator, mock_device_0, "Test", {"value": "0"})
    assert sensor_0.is_on is False
    
    # Test numeric values
    mock_device_num_true = {"id": 1, "name": "Test Device", "Test": {"value": 1}}
    sensor_num_true = EasylogCloudBinarySensor(mock_coordinator, mock_device_num_true, "Test", {"value": 1})
    assert sensor_num_true.is_on is True
    
    mock_device_num_false = {"id": 1, "name": "Test Device", "Test": {"value": 0}}
    sensor_num_false = EasylogCloudBinarySensor(mock_coordinator, mock_device_num_false, "Test", {"value": 0})
    assert sensor_num_false.is_on is False


def test_binary_sensor_device_info():
    """Test the device_info property of binary sensors."""
    from custom_components.ha_easylog_cloud.binary_sensor import EasylogCloudBinarySensor
    
    # Create a mock coordinator
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Test", {"value": "true"})
    device_info = sensor.device_info
    
    assert device_info["identifiers"] == {(DOMAIN, 1)}


async def test_binary_sensor_with_coordinator_updates(hass):
    """Test binary sensor behavior with coordinator updates."""
    from custom_components.ha_easylog_cloud.binary_sensor import EasylogCloudBinarySensor
    
    # Create a mock coordinator with data
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
        "Motion": {"value": "true", "unit": ""}
    }]
    
    mock_coordinator = type('MockCoordinator', (), {
        'data': mock_data
    })()
    
    mock_device = mock_data[0]
    sensor = EasylogCloudBinarySensor(mock_coordinator, mock_device, "Motion", {"value": "true"})
    
    # Test initial state
    assert sensor.is_on is True
    
    # Update coordinator data
    mock_data[0]["Motion"]["value"] = "false"
    
    # Test updated state
    assert sensor.is_on is False 