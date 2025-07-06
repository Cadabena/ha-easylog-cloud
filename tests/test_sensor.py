"""Test Home Assistant EasyLog Cloud sensor."""
from unittest.mock import patch
import pytest
from datetime import datetime, timezone
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_easylog_cloud.const import DOMAIN
from .const import MOCK_CONFIG


async def test_sensor_setup(hass):
    """Test sensor setup."""
    from custom_components.ha_easylog_cloud.sensor import async_setup_entry
    
    # Create a mock entry
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    
    # Mock coordinator data with various sensors
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
        "Temperature": {"value": 25.5, "unit": "°C"},
        "Humidity": {"value": 60, "unit": "%RH"},
        "CO2": {"value": 400, "unit": "ppm"},
        "Pressure": {"value": 1013.25, "unit": "hPa"},
        "WiFi Signal": {"value": -50, "unit": "dBm"},
        "Last Updated": {"value": "2024-01-01T12:00:00", "unit": ""},
        "VOC": {"value": 150, "unit": "ppb"},
        "PM2.5": {"value": 10, "unit": "µg/m³"},
        "Firmware Version": {"value": "1.2.3", "unit": ""},
        "MAC Address": {"value": "AA:BB:CC:DD:EE:FF", "unit": ""},
        "SSID": {"value": "MyWiFi", "unit": ""},
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
    
    # Verify that all sensors were added (excluding id, name, model)
    assert len(added_entities) == 11
    
    # Verify entity properties
    temp_sensor = next(e for e in added_entities if "Temperature" in e.name)
    assert temp_sensor.name == "Test Device Temperature"
    assert temp_sensor.unique_id == "1_temperature"
    assert temp_sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert temp_sensor.native_unit_of_measurement == "°C"
    assert temp_sensor.native_value == 25.5
    
    humidity_sensor = next(e for e in added_entities if "Humidity" in e.name)
    assert humidity_sensor.name == "Test Device Humidity"
    assert humidity_sensor.unique_id == "1_humidity"
    assert humidity_sensor.device_class == SensorDeviceClass.HUMIDITY
    assert humidity_sensor.native_unit_of_measurement == "%"  # Should be converted from %RH
    assert humidity_sensor.native_value == 60
    
    co2_sensor = next(e for e in added_entities if "CO2" in e.name)
    assert co2_sensor.name == "Test Device CO2"
    assert co2_sensor.unique_id == "1_co2"
    assert co2_sensor.device_class == SensorDeviceClass.CO2
    assert co2_sensor.native_unit_of_measurement == "ppm"
    assert co2_sensor.native_value == 400
    
    pressure_sensor = next(e for e in added_entities if "Pressure" in e.name)
    assert pressure_sensor.name == "Test Device Pressure"
    assert pressure_sensor.unique_id == "1_pressure"
    assert pressure_sensor.device_class == SensorDeviceClass.PRESSURE
    assert pressure_sensor.native_unit_of_measurement == "hPa"
    assert pressure_sensor.native_value == 1013.25
    
    signal_sensor = next(e for e in added_entities if "WiFi Signal" in e.name)
    assert signal_sensor.name == "Test Device WiFi Signal"
    assert signal_sensor.unique_id == "1_wifi_signal"
    assert signal_sensor.device_class == SensorDeviceClass.SIGNAL_STRENGTH
    assert signal_sensor.native_unit_of_measurement == "dBm"
    assert signal_sensor.native_value == -50
    assert signal_sensor.entity_category == EntityCategory.DIAGNOSTIC
    
    timestamp_sensor = next(e for e in added_entities if "Last Updated" in e.name)
    assert timestamp_sensor.name == "Test Device Last Updated"
    assert timestamp_sensor.unique_id == "1_last_updated"
    assert timestamp_sensor.device_class == SensorDeviceClass.TIMESTAMP
    assert timestamp_sensor.native_unit_of_measurement == ""  # Empty string for timestamp sensors
    assert isinstance(timestamp_sensor.native_value, datetime)
    
    voc_sensor = next(e for e in added_entities if "VOC" in e.name)
    assert voc_sensor.name == "Test Device VOC"
    assert voc_sensor.unique_id == "1_voc"
    assert voc_sensor.device_class is None  # No standard device class for VOC
    assert voc_sensor.native_unit_of_measurement == "ppb"
    assert voc_sensor.native_value == 150.0
    assert voc_sensor.state_class == "measurement"
    
    pm25_sensor = next(e for e in added_entities if "PM2.5" in e.name)
    assert pm25_sensor.name == "Test Device PM2.5"
    assert pm25_sensor.unique_id == "1_pm2.5"
    assert pm25_sensor.device_class is None  # No standard device class for PM2.5
    assert pm25_sensor.native_unit_of_measurement == "µg/m³"
    assert pm25_sensor.native_value == 10.0
    assert pm25_sensor.state_class == "measurement"
    
    firmware_sensor = next(e for e in added_entities if "Firmware Version" in e.name)
    assert firmware_sensor.name == "Test Device Firmware Version"
    assert firmware_sensor.unique_id == "1_firmware_version"
    assert firmware_sensor.device_class is None
    assert firmware_sensor.native_unit_of_measurement is None
    assert firmware_sensor.native_value == "1.2.3"
    assert firmware_sensor.entity_category == EntityCategory.DIAGNOSTIC


def test_device_class_guessing():
    """Test device class guessing logic."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator and device
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test temperature detection
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    assert temp_sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
    
    # Test humidity detection
    humidity_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Humidity", {"value": 60})
    assert humidity_sensor._attr_device_class == SensorDeviceClass.HUMIDITY
    
    # Test CO2 detection
    co2_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "CO2 Level", {"value": 400})
    assert co2_sensor._attr_device_class == SensorDeviceClass.CO2
    
    # Test pressure detection
    pressure_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Pressure", {"value": 1013})
    assert pressure_sensor._attr_device_class == SensorDeviceClass.PRESSURE
    
    # Test signal strength detection
    signal_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Signal Strength", {"value": -50})
    assert signal_sensor._attr_device_class == SensorDeviceClass.SIGNAL_STRENGTH
    
    # Test timestamp detection
    timestamp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Last Updated", {"value": "2024-01-01"})
    assert timestamp_sensor._attr_device_class == SensorDeviceClass.TIMESTAMP
    
    # Test unknown sensor
    unknown_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Unknown", {"value": 100})
    assert unknown_sensor._attr_device_class is None


def test_state_class_guessing():
    """Test state class guessing logic."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator and device
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test numeric sensors (should have measurement state class)
    voc_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "VOC", {"value": 150})
    assert voc_sensor._attr_state_class == "measurement"
    
    particulate_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "PM2.5", {"value": 10})
    assert particulate_sensor._attr_state_class == "measurement"
    
    aqi_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Air Quality", {"value": 50})
    assert aqi_sensor._attr_state_class == "measurement"
    
    # Test timestamp sensor (should not have state class)
    timestamp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Last Updated", {"value": "2024-01-01"})
    assert timestamp_sensor._attr_state_class is None
    
    # Test regular sensor (should not have state class)
    regular_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    assert regular_sensor._attr_state_class is None


def test_numeric_sensor_detection():
    """Test numeric sensor detection logic."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator and device
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test VOC detection
    voc_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "VOC Level", {"value": 150})
    assert voc_sensor._is_numeric_sensor("VOC Level") is True
    
    # Test particulate detection
    pm25_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "PM2.5", {"value": 10})
    assert pm25_sensor._is_numeric_sensor("PM2.5") is True
    
    # Test air quality detection
    aqi_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Air Quality Index", {"value": 50})
    assert aqi_sensor._is_numeric_sensor("Air Quality Index") is True
    
    # Test regular sensor
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    assert temp_sensor._is_numeric_sensor("Temperature") is False


def test_sensor_native_value_property():
    """Test the native_value property of sensors."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with data
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
        "Temperature": {"value": 25.5, "unit": "°C"},
        "Humidity": {"value": 60, "unit": "%"},
        "VOC": {"value": 150, "unit": "ppb"},
        "Last Updated": {"value": "2024-01-01T12:00:00", "unit": ""},
        "Invalid Timestamp": {"value": "invalid", "unit": ""},
        "Invalid Numeric": {"value": "not a number", "unit": ""},
    }]
    
    mock_coordinator = type('MockCoordinator', (), {
        'data': mock_data
    })()
    
    mock_device = mock_data[0]
    
    # Test temperature sensor
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    assert temp_sensor.native_value == 25.5
    
    # Test humidity sensor
    humidity_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Humidity", {"value": 60})
    assert humidity_sensor.native_value == 60
    
    # Test VOC sensor (numeric sensor)
    voc_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "VOC", {"value": 150})
    assert voc_sensor.native_value == 150.0
    
    # Test timestamp sensor
    timestamp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Last Updated", {"value": "2024-01-01T12:00:00"})
    timestamp_value = timestamp_sensor.native_value
    assert isinstance(timestamp_value, datetime)
    assert timestamp_value.year == 2024
    assert timestamp_value.month == 1
    assert timestamp_value.day == 1
    
    # Test invalid timestamp
    invalid_timestamp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Invalid Timestamp", {"value": "invalid"})
    # The sensor should return the raw value for non-timestamp sensors
    assert invalid_timestamp_sensor.native_value == "invalid"
    
    # Test invalid numeric sensor
    invalid_numeric_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Invalid Numeric", {"value": "not a number"})
    assert invalid_numeric_sensor.native_value == "not a number"  # Returns raw value for non-numeric sensors
    
    # Test sensor with device not found in coordinator
    non_existent_sensor = EasylogCloudSensor(mock_coordinator, {"id": 999, "name": "Non-existent"}, "Temperature", {"value": 25.5})
    assert non_existent_sensor.native_value is None
    
    # Test sensor with label not found in device
    missing_label_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Missing Label", {"value": 25.5})
    assert missing_label_sensor.native_value is None


def test_sensor_device_info():
    """Test the device_info property of sensors."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with data
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
    }]
    
    mock_coordinator = type('MockCoordinator', (), {
        'data': mock_data
    })()
    
    mock_device = mock_data[0]
    sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, 1)}
    assert device_info["name"] == "Test Device"
    assert device_info["manufacturer"] == "Lascar Electronics"
    assert device_info["model"] == "Test Model"
    
    # Test with device not found in coordinator
    non_existent_sensor = EasylogCloudSensor(mock_coordinator, {"id": 999, "name": "Non-existent"}, "Temperature", {"value": 25.5})
    device_info = non_existent_sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, 999)}
    assert device_info["name"] == "Device 999"
    assert device_info["manufacturer"] == "Lascar Electronics"


def test_humidity_unit_conversion():
    """Test humidity unit conversion from %RH to %."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator and device
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test %RH unit conversion
    humidity_sensor_rh = EasylogCloudSensor(mock_coordinator, mock_device, "Humidity", {"value": 60, "unit": "%RH"})
    assert humidity_sensor_rh.native_unit_of_measurement == "%"
    
    # Test RH% unit conversion
    humidity_sensor_rh2 = EasylogCloudSensor(mock_coordinator, mock_device, "Humidity", {"value": 60, "unit": "RH%"})
    assert humidity_sensor_rh2.native_unit_of_measurement == "%"
    
    # Test regular % unit (no conversion needed)
    humidity_sensor_percent = EasylogCloudSensor(mock_coordinator, mock_device, "Humidity", {"value": 60, "unit": "%"})
    assert humidity_sensor_percent.native_unit_of_measurement == "%"


def test_diagnostic_entity_categories():
    """Test that certain sensors are marked as diagnostic."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator and device
    mock_coordinator = type('MockCoordinator', (), {})()
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test diagnostic sensors
    firmware_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Firmware Version", {"value": "1.2.3"})
    assert firmware_sensor.entity_category == EntityCategory.DIAGNOSTIC
    
    mac_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "MAC Address", {"value": "AA:BB:CC:DD:EE:FF"})
    assert mac_sensor.entity_category == EntityCategory.DIAGNOSTIC
    
    ssid_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "SSID", {"value": "MyWiFi"})
    assert ssid_sensor.entity_category == EntityCategory.DIAGNOSTIC
    
    wifi_signal_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Wi-Fi Signal", {"value": -50})
    assert wifi_signal_sensor.entity_category == EntityCategory.DIAGNOSTIC
    
    wifi_signal_sensor2 = EasylogCloudSensor(mock_coordinator, mock_device, "WiFi Signal", {"value": -50})
    assert wifi_signal_sensor2.entity_category == EntityCategory.DIAGNOSTIC
    
    # Test non-diagnostic sensor
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    assert not hasattr(temp_sensor, 'entity_category') or temp_sensor.entity_category is None


async def test_sensor_with_coordinator_updates(hass):
    """Test sensor behavior with coordinator updates."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with data
    mock_data = [{
        "id": 1,
        "name": "Test Device",
        "model": "Test Model",
        "Temperature": {"value": 25.5, "unit": "°C"}
    }]
    
    mock_coordinator = type('MockCoordinator', (), {
        'data': mock_data
    })()
    
    mock_device = mock_data[0]
    sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    # Test initial state
    assert sensor.native_value == 25.5
    
    # Update coordinator data
    mock_data[0]["Temperature"]["value"] = 30.0
    
    # Test updated state
    assert sensor.native_value == 30.0


def test_sensor_native_value_timestamp_parsing():
    """Test native_value property with timestamp parsing."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with timestamp data
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 1,
            "name": "Test Device",
            "model": "Test Model",
            "Last Updated": {"value": "2024-01-01T12:00:00", "unit": ""}
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test timestamp parsing with ISO format
    timestamp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Last Updated", {"value": "2024-01-01T12:00:00"})
    result = timestamp_sensor.native_value
    assert isinstance(result, datetime)
    
    # Test timestamp parsing with naive datetime (should add UTC)
    timestamp_sensor2 = EasylogCloudSensor(mock_coordinator, mock_device, "Last Updated", {"value": "2024-01-01T12:00:00"})
    # Update coordinator data to have naive datetime
    mock_coordinator.data[0]["Last Updated"]["value"] = "2024-01-01T12:00:00"
    result2 = timestamp_sensor2.native_value
    assert isinstance(result2, datetime)
    assert result2.tzinfo is not None  # Should have timezone info added
    
    # Test timestamp parsing with invalid format
    mock_coordinator.data[0]["Last Updated"]["value"] = "invalid date"
    result3 = timestamp_sensor2.native_value
    assert result3 is None
    
    # Test timestamp parsing with non-string value
    mock_coordinator.data[0]["Last Updated"]["value"] = 12345
    result4 = timestamp_sensor2.native_value
    assert result4 is None


def test_sensor_native_value_numeric_sensor():
    """Test native_value property with numeric sensor conversion."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with VOC data
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 1,
            "name": "Test Device",
            "model": "Test Model",
            "VOC": {"value": "150.5", "unit": "ppb"}
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Test numeric sensor with valid float value
    voc_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "VOC", {"value": "150.5"})
    result = voc_sensor.native_value
    assert result == 150.5
    
    # Test numeric sensor with invalid value
    mock_coordinator.data[0]["VOC"]["value"] = "not a number"
    result2 = voc_sensor.native_value
    assert result2 is None


def test_sensor_native_value_exception_handling():
    """Test native_value property with exception handling."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with data that will cause exception
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 1,
            "name": "Test Device",
            "model": "Test Model",
            "Temperature": {"value": 25.5, "unit": "°C"}
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Create sensor
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    # Create a device dict that raises exception when accessing nested data
    class ExceptionDevice:
        def __getitem__(self, key):
            if key == "Temperature":
                raise Exception("Test exception")
            return {"value": 25.5}
    
    # Replace the device in coordinator data
    mock_coordinator.data[0] = ExceptionDevice()
    
    result = temp_sensor.native_value
    assert result is None


def test_sensor_native_value_device_not_found():
    """Test native_value property when device is not found in coordinator data."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with different device ID
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 999,  # Different ID
            "name": "Other Device",
            "model": "Other Model",
            "Temperature": {"value": 25.5, "unit": "°C"}
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Create sensor for device that doesn't exist in coordinator data
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    result = temp_sensor.native_value
    assert result is None


def test_sensor_native_value_label_not_found():
    """Test native_value property when label is not found in device data."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with device but missing the specific label
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 1,
            "name": "Test Device",
            "model": "Test Model",
            "Humidity": {"value": 60, "unit": "%"}  # Different label
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Create sensor for label that doesn't exist in device data
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    result = temp_sensor.native_value
    assert result is None


def test_sensor_device_info_fallback():
    """Test device_info property when device is not found in coordinator data."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with different device ID
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 999,  # Different ID
            "name": "Other Device",
            "model": "Other Model"
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Create sensor for device that doesn't exist in coordinator data
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    device_info = temp_sensor.device_info
    
    # Should return fallback device info
    assert device_info["identifiers"] == {(DOMAIN, 1)}
    assert device_info["name"] == "Device 1"
    assert device_info["manufacturer"] == "Lascar Electronics"
    assert "model" not in device_info  # No model in fallback 


def test_sensor_native_value_exception_in_value_access():
    """Test native_value property with exception when accessing device value."""
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    # Create a mock coordinator with data that will cause exception
    mock_coordinator = type('MockCoordinator', (), {
        'data': [{
            "id": 1,
            "name": "Test Device",
            "model": "Test Model",
            "Temperature": {"value": 25.5, "unit": "°C"}
        }]
    })()
    
    mock_device = {"id": 1, "name": "Test Device"}
    
    # Create sensor
    temp_sensor = EasylogCloudSensor(mock_coordinator, mock_device, "Temperature", {"value": 25.5})
    
    # Create a device dict that raises exception when accessing nested data
    class ExceptionDevice:
        def __getitem__(self, key):
            if key == "Temperature":
                return ExceptionValue()
            return {"value": 25.5}
    
    class ExceptionValue:
        def __getitem__(self, key):
            if key == "value":
                raise Exception("Test exception")
            return "°C"
    
    # Replace the device in coordinator data
    mock_coordinator.data[0] = ExceptionDevice()
    
    result = temp_sensor.native_value
    assert result is None 


async def test_sensor_native_value_timestamp_string_parsing_failure(hass):
    """Test sensor native_value with timestamp string parsing failure (line 104)."""
    # Create coordinator with device data
    from custom_components.ha_easylog_cloud.coordinator import EasylogCloudCoordinator
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    from homeassistant.components.sensor import SensorDeviceClass
    
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    coordinator.data = [
        {
            "id": 1,
            "name": "Test Device",
            "model": "EL-USB-TC",
            "Last Updated": {"value": "invalid timestamp string", "unit": ""}
        }
    ]
    
    # Create sensor for Last Updated
    sensor = EasylogCloudSensor(coordinator, coordinator.data[0], "Last Updated", {"value": "invalid timestamp string", "unit": ""})
    sensor._attr_device_class = SensorDeviceClass.TIMESTAMP
    
    # Get native value - should return None due to parsing failure
    value = sensor.native_value
    
    # Should return None when timestamp parsing fails
    assert value is None


async def test_sensor_native_value_numeric_sensor_float_conversion(hass):
    """Test sensor native_value with numeric sensor float conversion (lines 115-116)."""
    # Create coordinator with device data
    from custom_components.ha_easylog_cloud.coordinator import EasylogCloudCoordinator
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    coordinator.data = [
        {
            "id": 1,
            "name": "Test Device",
            "model": "EL-USB-TC",
            "VOC": {"value": "25.5", "unit": "ppm"}
        }
    ]
    
    # Create sensor for VOC (numeric sensor)
    sensor = EasylogCloudSensor(coordinator, coordinator.data[0], "VOC", {"value": "25.5", "unit": "ppm"})
    
    # Get native value - should convert to float
    value = sensor.native_value
    
    # Should return float value for numeric sensor
    assert value == 25.5


async def test_sensor_native_value_numeric_sensor_conversion_failure(hass):
    """Test sensor native_value with numeric sensor conversion failure (lines 115-116)."""
    # Create coordinator with device data
    from custom_components.ha_easylog_cloud.coordinator import EasylogCloudCoordinator
    from custom_components.ha_easylog_cloud.sensor import EasylogCloudSensor
    
    coordinator = EasylogCloudCoordinator(hass, "test_user", "test_pass")
    coordinator.data = [
        {
            "id": 1,
            "name": "Test Device",
            "model": "EL-USB-TC",
            "PM2.5": {"value": "invalid number", "unit": "µg/m³"}
        }
    ]
    
    # Create sensor for PM2.5 (numeric sensor)
    sensor = EasylogCloudSensor(coordinator, coordinator.data[0], "PM2.5", {"value": "invalid number", "unit": "µg/m³"})
    
    # Get native value - should return None due to conversion failure
    value = sensor.native_value
    
    # Should return None when numeric conversion fails
    assert value is None 