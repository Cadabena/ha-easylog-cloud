import logging
import re
from datetime import timedelta

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://www.easylogcloud.com/"

def parse_devicesArr_from_html(html_text):
    # 1. Try to find the devicesArr JavaScript array using more lenient matching
    match = re.search(r"devicesArr\s*=\s*(\[\s*new Device\(.*?\)\]);", html_text, re.DOTALL)
    if not match:
        _LOGGER.error("devicesArr not found in HTML")
        return []

    devices_js = match.group(1)

    # 2. Find all Channel(...) blocks inside the Device definition
    channel_blocks = re.findall(r"Channel\(([^)]+)\)", devices_js)
    if not channel_blocks:
        _LOGGER.error("No Channel() blocks found in devicesArr")
        return []

    # 3. Group channels into devices (every 3 Channel(...) per device)
    devices = []
    for i in range(0, len(channel_blocks), 3):
        dev = {"id": f"device_{i//3 + 1}", "name": f"EasyLog Device {i//3 + 1}"}
        for ch in channel_blocks[i:i+3]:
            fields = [s.strip().strip("'") for s in re.split(r",(?![^(]*\))", ch)]
            if len(fields) < 16:
                continue
            sensor_name = fields[2].lower()
            value = fields[14]
            try:
                value = float(value)
            except ValueError:
                pass
            dev[sensor_name] = value
        devices.append(dev)

    return devices

class EasylogCloudClient:
    def __init__(self, email, password, session: aiohttp.ClientSession):
        self._email = email
        self._password = password
        self._session = session
        self.display_name = None

    async def login_and_get_dashboard(self):
        async with self._session.get(LOGIN_URL) as resp:
            text = await resp.text()

        soup = BeautifulSoup(text, "html.parser")

        # Get login form tokens
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

        # Extract display name
        soup = BeautifulSoup(html, "html.parser")
        username_span = soup.find("span", {"id": "username"})
        self.display_name = username_span.text.strip() if username_span else self._email

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
            name="ha_easylog_cloud",
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self):
        try:
            data = await self.client.get_devices()
            _LOGGER.debug("Fetched data: %s", data)
            return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
