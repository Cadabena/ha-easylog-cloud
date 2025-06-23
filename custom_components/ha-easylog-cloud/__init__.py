import asyncio
import logging
import re

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://www.easylogcloud.com/"

def parse_devicesArr_from_html(html):
    """Extract sensor data from the devicesArr JavaScript."""
    match = re.search(r"var\s+devicesArr\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not match:
        _LOGGER.error("devicesArr not found in HTML")
        return []

    devices_js = match.group(1)
    channels_blocks = re.findall(r"Channel\((.*?)\)", devices_js, re.DOTALL)
    devices = []

    for i, raw in enumerate(channels_blocks):
        parts = re.findall(r"'[^']*'|[^,]+", raw.strip())
        if len(parts) < 16:
            continue

        name = parts[2].strip().strip("'")
        value = parts[14].strip().strip("'")
        unit = parts[15].strip().strip("'")

        # group sensors by device every 3 channels
        if i % 3 == 0:
            devices.append({})
        sensor_type = name.lower()
        devices[-1]["name"] = f"EasyLog Device {i//3 + 1}"
        devices[-1][sensor_type] = float(value) if value.replace('.', '', 1).isdigit() else value

    for i, d in enumerate(devices):
        d["id"] = f"device_{i}"

    return devices

class EasylogCloudClient:
    def __init__(self, email, password, session: aiohttp.ClientSession):
        self._email = email
        self._password = password
        self._session = session

    async def login_and_get_dashboard(self):
        async with self._session.get(LOGIN_URL) as resp:
            text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")

        def val(name):
            el = soup.find("input", {"name": name})
            return el["value"] if el else ""

        payload = {
            "__EVENTTARGET": "ctl00$cph1$signin",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": val("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": val("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": val("__EVENTVALIDATION"),
            "ctl00$cph1$username1": self._email,
            "ctl00$cph1$password": self._password,
            "ctl00$cph1$fromcookie": "false",
            "ctl00$cph1$rememberme": "on",
        }

        async with self._session.post(LOGIN_URL, data=payload) as resp:
            html = await resp.text()
            if "devicesArr" not in html:
                raise Exception("Login failed or device data not found.")
            return html

    async def get_devices(self):
        html = await self.login_and_get_dashboard()
        return parse_devicesArr_from_html(html)

class EasylogCloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, email, password, session):
        self.client = EasylogCloudClient(email, password, session)
        super().__init__(
            hass,
            _LOGGER,
            name="EasyLog Cloud",
            update_interval=asyncio.timedelta(minutes=5),
        )

    async def _async_update_data(self):
        try:
            return await self.client.get_devices()
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
