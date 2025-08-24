from __future__ import annotations

import logging
from datetime import datetime
from datetime import timezone

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    _LOGGER.debug("Coordinator data: %s", coordinator.data)

    for device in coordinator.data:
        _LOGGER.warning(
            "Available fields for %s: %s", device["name"], list(device.keys())
        )
        for label, data in device.items():
            if label in ("id", "name", "model"):
                continue
            _LOGGER.error(
                "Adding sensor for device '%s': %s = %s %s",
                device["name"],
                label,
                data.get("value") if isinstance(data, dict) else data,
                data.get("unit") if isinstance(data, dict) else "",
            )
            entities.append(EasylogCloudSensor(coordinator, device, label, data))

    async_add_entities(entities)


class EasylogCloudSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device, label, data):
        super().__init__(coordinator)
        self.device_id = device["id"]
        self.label = label
        self._attr_name = f"{device['name']} {label}"
        self._attr_unique_id = f"{device['id']}_{label.lower().replace(' ', '_')}"
        self._attr_device_class = self._guess_device_class(label)
        self._attr_state_class = self._guess_state_class(label)

        # Store the last known good value
        self._last_value = None

        # Fix humidity unit: replace %RH with % (required by HA)
        raw_unit = data.get("unit") if isinstance(data, dict) else None
        if self._attr_device_class == SensorDeviceClass.HUMIDITY and raw_unit in (
            "%RH",
            "RH%",
        ):
            self._attr_native_unit_of_measurement = "%"
        elif self._attr_device_class or self._is_numeric_sensor(label):
            self._attr_native_unit_of_measurement = raw_unit
        else:
            self._attr_native_unit_of_measurement = None

        if label.lower() in [
            "firmware version",
            "mac address",
            "ssid",
            "wi-fi signal",
            "wifi signal",
        ]:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _guess_device_class(self, label: str):
        label = label.lower()
        if "temp" in label:
            return SensorDeviceClass.TEMPERATURE
        if "humidity" in label:
            return SensorDeviceClass.HUMIDITY
        if "co2" in label or "carbon dioxide" in label:
            return SensorDeviceClass.CO2
        if "pressure" in label:
            return SensorDeviceClass.PRESSURE
        if "signal" in label:
            return SensorDeviceClass.SIGNAL_STRENGTH
        if "last updated" in label:
            return SensorDeviceClass.TIMESTAMP
        # No standard device class for VOC, particulates, or air quality in HA as of 2024
        return None

    def _guess_state_class(self, label: str):
        # For VOC, particulates, air quality, and other numeric sensors, set as measurement
        if self._is_numeric_sensor(label):
            return "measurement"
        # For timestamp, do not set state_class
        return None

    def _is_numeric_sensor(self, label: str):
        label = label.lower()
        keywords = ["voc", "particulate", "pm2.5", "pm10", "air quality", "aqi"]
        return any(k in label for k in keywords)

    @property
    def native_value(self):
        # Always look up the latest device data from the coordinator
        device = next(
            (d for d in self.coordinator.data if d["id"] == self.device_id), None
        )
        value = None
        if device and self.label in device:
            try:
                value = device[self.label]["value"]
                _LOGGER.debug(
                    "Sensor %s.%s: fetched value %s", self.device_id, self.label, value
                )
                # If value is 'unknown' or None, return last known value
                if value in (None, "unknown"):
                    _LOGGER.debug(
                        "Sensor %s.%s: value is unknown or None, using last known value %s",
                        self.device_id,
                        self.label,
                        self._last_value,
                    )
                    return self._last_value

                # For timestamp sensors, parse value
                if self._attr_device_class == SensorDeviceClass.TIMESTAMP and value:
                    if isinstance(value, str):
                        try:
                            dt = datetime.fromisoformat(value)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            self._last_value = dt
                            return dt
                        except Exception:
                            _LOGGER.warning(
                                "Failed to parse timestamp value '%s' for %s",
                                value,
                                self.label,
                            )
                            return self._last_value
                    elif isinstance(value, datetime):
                        self._last_value = value
                        return value
                    return self._last_value

                # For numeric sensors, ensure value is a number
                if self._is_numeric_sensor(self.label):
                    try:
                        num_value = float(value)
                        self._last_value = num_value
                        return num_value
                    except (TypeError, ValueError):
                        _LOGGER.warning(
                            "Value for %s is not numeric: %s", self.label, value
                        )
                        return self._last_value

                # For all other sensors, just store and return the value
                self._last_value = value
                return value
            except Exception as e:
                _LOGGER.warning(
                    "native_value error for %s on %s: %s",
                    self.label,
                    device.get("name"),
                    e,
                )
                return self._last_value
        else:
            _LOGGER.debug(
                "Sensor %s.%s: device or label not found in coordinator data",
                self.device_id,
                self.label,
            )
            return self._last_value

    @property
    def device_info(self):
        # Get the latest device info from coordinator data
        device = next(
            (d for d in self.coordinator.data if d["id"] == self.device_id), None
        )
        if device:
            return {
                "identifiers": {
                    (DOMAIN, self.device_id),
                },
                "name": device["name"],
                "manufacturer": "Lascar Electronics",
                "model": device["model"],
            }
        return {
            "identifiers": {
                (DOMAIN, self.device_id),
            },
            "name": f"Device {self.device_id}",
            "manufacturer": "Lascar Electronics",
        }
