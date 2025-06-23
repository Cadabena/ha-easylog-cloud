DOMAIN = "home_assistant_easylog_cloud"
CONF_USERNAME = "email"
CONF_PASSWORD = "password"
PLATFORMS = ["sensor"]
STARTUP_MESSAGE = "Starting Home Assistant EasyLog Cloud integration"


# config_flow.py
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD

class EasylogCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="EasyLog Cloud", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
