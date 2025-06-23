from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

SENSOR_TYPES = {
    "temperature": {"name": "Temperature", "unit": "°C", "device_class": "temperature"},
    "humidity": {"name": "Humidity", "unit": "%", "device_class": "humidity"},
    "co2": {"name": "Carbon Dioxide", "unit": "ppm", "device_class": "carbon_dioxide"},
}

async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    for device in coordinator.data:
        device_id = device.get("id")
        for sensor_type in SENSOR_TYPES:
            if sensor_type in device:
                sensors.append(
                    EasylogCloudSensor(coordinator, device_id, device, sensor_type)
                )
    async_add_devices(sensors)

class EasylogCloudSensor(SensorEntity):
    def __init__(self, coordinator, device_id, device, sensor_type):
        self.coordinator = coordinator
        self.device = device
        self.device_id = device_id
        self.sensor_type = sensor_type

        st = SENSOR_TYPES[sensor_type]
        self._attr_name = f"{device['name']} {st['name']}"
        self._attr_unique_id = f"{device_id}-{sensor_type}"
        self._attr_native_unit_of_measurement = st["unit"]
        self._attr_device_class = st["device_class"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device["name"],
            manufacturer="Lascar Electronics",
            model="EL-IOT-CO2",
        )

    @property
    def native_value(self):
        return self.device.get(self.sensor_type)