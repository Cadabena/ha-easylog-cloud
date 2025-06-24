from __future__ import annotations

import logging
import re
from bs4 import BeautifulSoup
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class EasylogCloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self._username = username
        self._password = password
        self._session = async_get_clientsession(hass)
        self._cookies = None
        self.account_name = None

    async def _async_update_data(self):
        try:
            await self.authenticate()
            html = await self.fetch_devices_page()
            devices_js = self._extract_devices_arr_from_html(html)
            devices = self._extract_device_data(devices_js, html)
            _LOGGER.debug("Parsed devices: %s", devices)
            return devices
        except Exception as e:
            _LOGGER.error("Failed to fetch device data: %s", e)
            return []

    async def authenticate(self):
        login_url = "https://www.easylogcloud.com/"
        response = await self._session.get(login_url)
        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")

        viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
        viewstategen = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})["value"]

        payload = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "ctl00$cph1$username1": self._username,
            "ctl00$cph1$password": self._password,
            "ctl00$cph1$rememberme": "on",
            "ctl00$cph1$signin": "Sign In",
        }

        post_resp = await self._session.post(login_url, data=payload)
        self._cookies = post_resp.cookies
        _LOGGER.debug("Login status: %s", post_resp.status)

    async def fetch_devices_page(self):
        url = "https://www.easylogcloud.com/devices.aspx"
        response = await self._session.get(url, cookies=self._cookies)
        html = await response.text()
        return html

    def _extract_devices_arr_from_html(self, html: str) -> str:
        match = re.search(r"var devicesArr = \[(.*?)\];", html, re.DOTALL)
        if not match:
            _LOGGER.error("devicesArr not found in HTML")
            _LOGGER.debug("Full HTML: %s", html[:5000])
            return ""
        return match.group(1)

    def _extract_device_data(self, devices_js: str, html: str):
        devices = []
        # Match full Device blocks, including Channel arrays
        device_blocks = re.findall(r"new Device\((.*?\[.*?new Channel.*?\])\s*,\s*\[\],-1,false,\d+,\d+\)", devices_js, re.DOTALL)

        for block in device_blocks:
            # Split the block only up to the start of the channel array
            parts = re.split(r",\s*\[new Channel", block, maxsplit=1)
            device_fields = re.split(r"(?<!\\),", parts[0], maxsplit=50)
            channel_part = "[new Channel" + parts[1]

            try:
                device_id = int(device_fields[0].strip())
                model = device_fields[2].strip("' ")
                name = device_fields[4].strip("' ")
            except (IndexError, ValueError) as e:
                _LOGGER.warning("Failed to parse device fields: %s", e)
                continue

            device_data = {
                "id": device_id,
                "name": name,
                "model": model,
            }

            channels = re.findall(r"new Channel\((.*?)\)", channel_part, re.DOTALL)
            for chan in channels:
                chan_fields = re.split(r"(?<!\\),", chan)
                if len(chan_fields) < 16:
                    continue
                label = chan_fields[2].strip("' ")
                value = chan_fields[14].strip("' ")
                unit = chan_fields[15].strip("' ")
                _LOGGER.debug("Device %s: Channel %s = %s %s", name, label, value, unit)

                device_data[label] = {
                    "value": value,
                    "unit": unit,
                }

            _LOGGER.debug("Final device object: %s", device_data)
            devices.append(device_data)

        # Extract account name from HTML
        soup = BeautifulSoup(html, "html.parser")
        username_span = soup.find("span", {"id": "username"})
        if username_span:
            self.account_name = username_span.text.strip()
            _LOGGER.debug("Extracted account name: %s", self.account_name)

        return devices

