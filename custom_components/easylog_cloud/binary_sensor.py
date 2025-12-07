from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for device in coordinator.data:
        for label, data in device.items():
            if label in {"id", "name", "model"}:
                continue
            if isinstance(data, dict) and "value" in data:
                if _is_binary(data):
                    entities.append(
                        EasylogCloudBinarySensor(coordinator, device, label, data)
                    )

    async_add_entities(entities)


def _is_binary(data: dict) -> bool:
    try:
        val = data.get("value")
        if isinstance(val, str):
            return val.lower() in {"true", "false", "on", "off", "1", "0"}
        if isinstance(val, (int, float)):
            return val in {0, 1}
    except Exception:
        pass
    return False


class EasylogCloudBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, device, label, data):
        super().__init__(coordinator)
        self.device = device
        self.label = label
        self._attr_name = f"{device['name']} {label}"
        self._attr_unique_id = f"{device['id']}_{label.lower().replace(' ', '_')}"
        self._attr_device_class = self._guess_device_class(label)

    def _guess_device_class(self, label):
        label = label.lower()
        if "motion" in label:
            return BinarySensorDeviceClass.MOTION
        if "contact" in label or "door" in label:
            return BinarySensorDeviceClass.DOOR
        if "window" in label:
            return BinarySensorDeviceClass.WINDOW
        if "battery" in label:
            return BinarySensorDeviceClass.BATTERY
        if "power" in label:
            return BinarySensorDeviceClass.POWER
        return None

    @property
    def is_on(self):
        val = self.device.get(self.label, {}).get("value")
        if isinstance(val, str):
            return val.lower() in {"true", "on", "1"}
        return bool(val)

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.device["id"])}}
