from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

SENSOR_TYPES = {
    "temperature": {"name": "Temperature", "unit": "°C", "device_class": "temperature"},
    "humidity": {"name": "Humidity", "unit": "%", "device_class": "humidity"},
    "carbon dioxide": {"name": "CO2", "unit": "ppm", "device_class": "carbon_dioxide"},
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for device in coordinator.data:
        for key, desc in SENSOR_TYPES.items():
            if key in device:
                entities.append(EasylogCloudSensor(coordinator, device, key))

    async_add_entities(entities)

class EasylogCloudSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device, kind):
        super().__init__(coordinator)
        self.device = device
        self.kind = kind
        self._attr_name = f"{device['name']} {SENSOR_TYPES[kind]['name']}"
        self._attr_unique_id = f"{device['id']}_{kind}"
        self._attr_unit_of_measurement = SENSOR_TYPES[kind]['unit']
        self._attr_device_class = SENSOR_TYPES[kind]['device_class']

    @property
    def native_value(self):
        return self.device.get(self.kind)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.device["id"])},
            "name": self.device["name"],
            "manufacturer": "Lascar Electronics",
            "model": "EL-IOT-CO2",
        }