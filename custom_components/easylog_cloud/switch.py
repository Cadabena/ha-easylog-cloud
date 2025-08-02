from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for device in coordinator.data:
        for label, data in device.items():
            if isinstance(data, dict) and "switch" in label.lower():
                entities.append(EasylogCloudSwitch(coordinator, device, label, data))

    async_add_entities(entities)


class EasylogCloudSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, device, label, data):
        super().__init__(coordinator)
        self.device = device
        self.label = label
        self._attr_name = f"{device['name']} {label}"
        self._attr_unique_id = f"{device['id']}_{label.lower().replace(' ', '_')}"
        self._state = data.get("value", "off") == "on"

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        # Placeholder: you would call the appropriate API to switch this on
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        # Placeholder: you would call the appropriate API to switch this off
        self._state = False
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.device["id"])},
            "name": self.device["name"],
            "manufacturer": "Lascar Electronics",
            "model": self.device["model"],
        }
