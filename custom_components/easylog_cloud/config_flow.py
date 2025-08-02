from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries

from .api import (
    HAEasylogCloudApiClient,
)  # noqa: E402  (import after top-level for tests)
from .const import CONF_PASSWORD
from .const import CONF_USERNAME
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EasylogCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._errors = {}

    async def async_step_user(self, user_input=None):
        self._errors = {}

        if user_input is not None:
            valid, name = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if valid:
                return self.async_create_entry(
                    title=name or user_input[CONF_USERNAME],  # fallback to email
                    data=user_input,
                )
            else:
                self._errors["base"] = "auth"

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(
        self, username: str, password: str
    ) -> tuple[bool, str | None]:
        try:
            api_client = HAEasylogCloudApiClient(self.hass, username, password)
            await api_client.authenticate()
            html = await api_client.fetch_devices_page()
            devices_js = api_client._extract_devices_arr_from_html(html)
            api_client._extract_device_list(devices_js, html)

            if api_client.account_name:
                return True, api_client.account_name
            return True, None
        except Exception as e:
            _LOGGER.error("Credential test failed: %s", e)
            return False, None
