from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import HAEasylogCloudApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EasylogCloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self.api_client = HAEasylogCloudApiClient(hass, username, password)
        self._cookies = None
        self.account_name = None

    async def _async_update_data(self):
        return await self.api_client.async_get_devices_data()

    async def authenticate(self):
        """Authenticate using the API client."""
        await self.api_client.authenticate()
        self._cookies = self.api_client._cookies

    async def fetch_devices_page(self):
        """Fetch devices page using the API client."""
        return await self.api_client.fetch_devices_page()

    def _extract_devices_arr_from_html(self, html: str) -> str:
        """Extract devices array from HTML using the API client."""
        return self.api_client._extract_devices_arr_from_html(html)

    def _extract_device_list(self, devices_js: str, html: str):
        """Extract device list using the API client."""
        devices = self.api_client._extract_device_list(devices_js, html)
        self.account_name = self.api_client.account_name
        return devices
