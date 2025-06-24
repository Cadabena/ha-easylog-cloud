# config_flow.py
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, PLATFORMS
from .coordinator import EasylogCloudClient

import logging
_LOGGER = logging.getLogger(__name__)

class EasylogCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._errors = {}

    async def async_step_user(self, user_input=None):
        self._errors = {}

        if user_input is not None:
            valid = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if valid:
                return self.async_create_entry(title=valid, data=user_input)
            else:
                self._errors["base"] = "auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=self._errors,
        )

    async def _test_credentials(self, username, password):
        try:
            session = async_create_clientsession(self.hass)
            client = EasylogCloudClient(username, password, session)
            html = await client.login_and_get_dashboard()
            if "devicesArr" in html:
                return client.display_name or username
        except Exception as e:
            _LOGGER.exception("Auth test failed")
        return None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EasylogCloudOptionsFlowHandler(config_entry)

class EasylogCloudOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(x, default=self.options.get(x, True)): bool
                for x in sorted(PLATFORMS)
            }),
        )

    async def _update_options(self):
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_USERNAME),
            data=self.options
        )
