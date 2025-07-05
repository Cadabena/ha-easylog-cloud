"""API client for EasyLog Cloud integration (stub)."""

import logging
import re
import datetime
from bs4 import BeautifulSoup
import xmltodict
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

class HAEasylogCloudApiClient:
    def __init__(self, hass, username, password):
        self._username = username
        self._password = password
        self._session = async_get_clientsession(hass)
        self._cookies = None
        self.account_name = None

    async def async_get_devices_data(self):
        try:
            await self.authenticate()
            html = await self.fetch_devices_page()
            devices_js = self._extract_devices_arr_from_html(html)
            device_list = self._extract_device_list(devices_js, html)
            if not device_list:
                _LOGGER.error("No devices found in device_list! devices_js: %s", devices_js)
            # Now fetch live data for each device
            live_devices = []
            for device in device_list:
                device_id = device["id"]
                url = f"https://www.easylogcloud.com/devicedata.asmx/currentStatus?index=1&sensorId={device_id}"
                headers = {"Accept": "application/json"}
                async with self._session.get(url, cookies=self._cookies, headers=headers) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        text = await resp.text()
                        try:
                            data = xmltodict.parse(text)
                        except Exception:
                            _LOGGER.error("API did not return JSON or valid XML. Response text: %s", text)
                            continue
                        # Try to extract JSON from inside the XML (common for .NET web services)
                        # Look for a key like 'string' or similar
                        if isinstance(data, dict) and 'string' in data:
                            import json
                            try:
                                data = json.loads(data['string'])
                            except Exception:
                                _LOGGER.error("Failed to parse JSON from XML 'string' node: %s", data['string'])
                                continue
                d = data.get("d") or data.get("deviceStatus") or {}
                if not d:
                    _LOGGER.error("No data returned from API for device %s! Response: %s", device_id, data)
                # Build device data structure
                mac_addr = device.get("MAC Address") or {"value": ""}
                firmware = device.get("Firmware Version") or {"value": ""}
                ssid = device.get("SSID") or {"value": ""}
                wifi_signal = device.get("WiFi Signal") or {"value": ""}
                # Parse lastCommFormatted to a datetime object if possible
                last_comm = d.get("lastCommFormatted", "")
                if isinstance(last_comm, str) and last_comm:
                    try:
                        dt = datetime.datetime.strptime(last_comm, "%d/%m/%Y %H:%M:%S")
                        last_comm_dt = dt_util.as_local(dt)
                    except Exception:
                        last_comm_dt = None
                else:
                    last_comm_dt = None
                device_data = {
                    "id": device_id,
                    "name": d.get("sensorName", device["name"]),
                    "model": device["model"],
                    "MAC Address": {"value": mac_addr.get("value", ""), "unit": ""},
                    "Firmware Version": {"value": d.get("firmwareVersion", firmware.get("value", "")), "unit": ""},
                    "SSID": {"value": ssid.get("value", ""), "unit": ""},
                    "WiFi Signal": {"value": d.get("rssi", wifi_signal.get("value", "")), "unit": None},
                    "Last Updated": {"value": last_comm_dt, "unit": ""},
                }
                # Add channels
                channels = []
                if "channels" in d:
                    if isinstance(d["channels"], dict) and "channelDetails" in d["channels"]:
                        details = d["channels"]["channelDetails"]
                        if isinstance(details, list):
                            channels = details
                        else:
                            channels = [details]
                    elif isinstance(d["channels"], list):
                        channels = d["channels"]
                for channel in channels:
                    label = channel.get("channelLabel", "")
                    value = channel.get("reading", "")
                    unit = channel.get("unit", "")
                    # Convert to int if possible
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = None
                    # Convert invalid values like '--.--' to None
                    if value in ['--.--', '---', 'N/A', '']:
                        value = None
                    device_data[label] = {"value": value, "unit": unit}
                # Defensive check: ensure 'Last Updated' is always a datetime or None
                if not (device_data["Last Updated"]["value"] is None or hasattr(device_data["Last Updated"]["value"], "tzinfo")):
                    device_data["Last Updated"]["value"] = None
                live_devices.append(device_data)
            if not live_devices:
                _LOGGER.error("No live devices found! device_list: %s", device_list)
            _LOGGER.debug("API client update complete. Found %d devices with data", len(live_devices))
            return live_devices
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

    async def async_set_title(self, title):
        # Stub method for setting a title
        pass

    async def api_wrapper(self, method, url):
        # Stub method for API wrapper
        return None 