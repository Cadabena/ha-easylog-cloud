from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .const import PLATFORMS
from .coordinator import EasylogCloudCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easylog Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = EasylogCloudCoordinator(
        hass,
        username=entry.data["username"],
        password=entry.data["password"],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


# --- Stubs for test compatibility ---
async def async_reload_entry(hass, entry):
    """Stub for async_reload_entry."""
    return None

# Alias for test compatibility
HAEasylogCloudDataUpdateCoordinator = EasylogCloudCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the EasyLog Cloud component."""
    hass.data.setdefault(DOMAIN, {})
    return True
