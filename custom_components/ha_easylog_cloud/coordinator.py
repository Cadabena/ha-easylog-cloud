from __future__ import annotations

import logging
import re
import datetime
from datetime import timedelta
from bs4 import BeautifulSoup
import xmltodict

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .api import HAEasylogCloudApiClient

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

    def _extract_device_list(self, devices_js: str, html: str):
        devices = []
        # Use regex to match each 'new Device(...)' block
        device_blocks = re.findall(r'new Device\((.*?\[.*?new Channel.*?\][^)]*)\)', devices_js)
        for block in device_blocks:
            # Log the device block for debugging
            _LOGGER.error("Device block: %s", block)
            # Now parse block as before
            parts = re.split(r",\s*\[new Channel", block, maxsplit=1)
            device_fields = re.split(r"(?<!\\),", parts[0], maxsplit=50)
            # Check for required indexes before using them
            required_indexes = [0, 2, 4, 5, 16, 17, 28, 34]
            if len(device_fields) < max(required_indexes) + 1:
                _LOGGER.warning("Skipping device, not enough fields: %d found", len(device_fields))
                continue
            try:
                device_id = int(device_fields[0].strip())
                model = device_fields[2].strip("' ")
                name = device_fields[4].strip("' ")
                mac = device_fields[5].strip("' ") if len(device_fields) > 5 else ""
                firmware = device_fields[16].strip("' ") if len(device_fields) > 16 else ""
                ssid = device_fields[17].strip("' ") if len(device_fields) > 17 else ""
                wifi_signal = device_fields[28].strip() if len(device_fields) > 28 else ""
                last_sync_raw = device_fields[34].strip("' ") if len(device_fields) > 34 else ""
                try:
                    dt = datetime.datetime.strptime(last_sync_raw, "%d/%m/%Y %H:%M:%S")
                    last_sync = dt_util.as_local(dt)
                except Exception:
                    last_sync = None
                device_data = {
                    "id": device_id,
                    "name": name,
                    "model": model,
                    "MAC Address": {"value": mac, "unit": ""},
                    "Firmware Version": {"value": firmware, "unit": ""},
                    "SSID": {"value": ssid, "unit": ""},
                    "WiFi Signal": {"value": wifi_signal, "unit": None},
                    "Last Updated": {"value": last_sync, "unit": ""},
                }
                devices.append(device_data)
            except (IndexError, ValueError) as e:
                _LOGGER.warning("Failed to parse device fields: %s", e)
                continue
        soup = BeautifulSoup(html, "html.parser")
        username_span = soup.find("span", {"id": "username"})
        if username_span:
            self.account_name = username_span.text.strip()
            _LOGGER.debug("Extracted account name: %s", self.account_name)
        return devices
