from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    _LOGGER.error(coordinator.data)
    for device in coordinator.data:
        for label, data in device.items():
            if label in ("id", "name", "model"):
                continue
            _LOGGER.error("Adding sensor for device '%s': %s = %s %s", device["name"], label, data.get("value"), data.get("unit"))
            entities.append(EasylogCloudSensor(coordinator, device, label, data))

    async_add_entities(entities)

class EasylogCloudSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device, label, data):
        super().__init__(coordinator)
        self.device = device
        self.label = label
        self._attr_name = f"{device['name']} {label}"
        self._attr_unique_id = f"{device['id']}_{label.lower().replace(' ', '_')}"
        self._attr_native_unit_of_measurement = data.get("unit")
        self._attr_device_class = self._guess_device_class(label)

    def _guess_device_class(self, label: str):
        label = label.lower()
        if "temp" in label:
            return SensorDeviceClass.TEMPERATURE
        if "humidity" in label:
            return SensorDeviceClass.HUMIDITY
        if "co2" in label or "carbon dioxide" in label:
            return SensorDeviceClass.CO2
        return None

    @property
    def native_value(self):
        return self.device[self.label]["value"]

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.device["id"]),},
            "name": self.device["name"],
            "manufacturer": "Lascar Electronics",
            "model": self.device["model"],
        }
