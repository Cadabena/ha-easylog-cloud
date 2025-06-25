from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    _LOGGER.debug("Coordinator data: %s", coordinator.data)

    for device in coordinator.data:
        _LOGGER.warning("Available fields for %s: %s", device["name"], list(device.keys()))
        for label, data in device.items():
            if label in ("id", "name", "model"):
                continue
            _LOGGER.error("Adding sensor for device '%s': %s = %s %s",
                          device["name"], label, data.get("value") if isinstance(data, dict) else data,
                          data.get("unit") if isinstance(data, dict) else "")
            entities.append(EasylogCloudSensor(coordinator, device, label, data))

    async_add_entities(entities)

class EasylogCloudSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device, label, data):
        super().__init__(coordinator)
        self.device = device
        self.label = label
        self._attr_name = f"{device['name']} {label}"
        self._attr_unique_id = f"{device['id']}_{label.lower().replace(' ', '_')}"
        self._attr_device_class = self._guess_device_class(label)

        self._attr_native_unit_of_measurement = (
            data.get("unit") if isinstance(data, dict) and self._attr_device_class else None
        )

        if label.lower() in ["firmware version", "mac address", "ssid", "wi-fi signal", "wifi signal"]:
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
        return None

    @property
    def native_value(self):
        try:
            return self.device[self.label]["value"]
        except Exception as e:
            _LOGGER.warning("native_value error for %s on %s: %s", self.label, self.device.get("name"), e)
            return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.device["id"]),},
            "name": self.device["name"],
            "manufacturer": "Lascar Electronics",
            "model": self.device["model"],
        }
