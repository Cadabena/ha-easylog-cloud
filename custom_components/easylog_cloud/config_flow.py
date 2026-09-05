from __future__ import annotations

import logging

from homeassistant import config_entries
import voluptuous as vol

from .api import (  # noqa: E402  (import after top-level for tests)
    HAEasylogCloudApiClient,
)
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EasylogCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            valid, name = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if valid:
                return self.async_create_entry(
                    title=name or user_input[CONF_USERNAME],  # fallback to email
                    data=user_input,
                )
            else:
                errors["base"] = "auth"

        return await self._show_config_form(user_input, errors)

    async def _show_config_form(self, user_input, errors):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
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
