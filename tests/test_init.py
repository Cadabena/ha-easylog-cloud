"""Test Home Assistant EasyLog Cloud setup process."""
from unittest.mock import patch

import pytest
from custom_components.ha_easylog_cloud import (
    async_reload_entry,
)
from custom_components.ha_easylog_cloud import (
    async_setup_entry,
)
from custom_components.ha_easylog_cloud import (
    async_unload_entry,
)
from custom_components.ha_easylog_cloud import (
    HAEasylogCloudDataUpdateCoordinator,
)
from custom_components.ha_easylog_cloud.const import (
    DOMAIN,
)
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG


# We can pass fixtures as defined in conftest.py to tell pytest to use the fixture
# for a given test. We can also leverage fixtures and mocks that are available in
# Home Assistant using the pytest_homeassistant_custom_component plugin.
# Assertions allow you to verify that the return value of whatever is on the left
# side of the assertion matches with the right side.
async def test_setup_unload_and_reload_entry(hass, bypass_get_data):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # Mock the integration loading
    with patch("homeassistant.loader.async_get_integration") as mock_get_integration:
        # Create a mock integration
        async def mock_resolve_dependencies(self):
            return True

        mock_integration = type(
            "MockIntegration",
            (),
            {
                "domain": DOMAIN,
                "config_flow": True,
                "async_get_flow_handler": lambda: None,
                "disabled": False,
                "is_built_in": False,
                "documentation": None,
                "resolve_dependencies": mock_resolve_dependencies,
                "dependencies": [],
            },
        )()
        mock_get_integration.return_value = mock_integration

        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ):
            # Set up the entry and assert that the values set during setup are where we expect
            # them to be. Because we have patched the HAEasylogCloudDataUpdateCoordinator.async_get_devices_data
            # call, no code from custom_components/ha_easylog_cloud/api.py actually runs.
            assert await async_setup_entry(hass, config_entry)
            assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
            assert isinstance(
                hass.data[DOMAIN][config_entry.entry_id],
                HAEasylogCloudDataUpdateCoordinator,
            )

            # Reload the entry and assert that the data from above is still there
            assert await async_reload_entry(hass, config_entry) is None
            assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
            assert isinstance(
                hass.data[DOMAIN][config_entry.entry_id],
                HAEasylogCloudDataUpdateCoordinator,
            )

            # Unload the entry and verify that the data has been removed
            assert await async_unload_entry(hass, config_entry)
            assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_exception(hass, error_on_get_data):
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # In this case we are testing the condition where async_setup_entry raises
    # ConfigEntryNotReady using the `error_on_get_data` fixture which simulates
    # an error.
    with pytest.raises(ConfigEntryNotReady):
        assert await async_setup_entry(hass, config_entry)


async def test_async_setup(hass):
    """Test async_setup function."""
    from custom_components.ha_easylog_cloud import async_setup

    # Test that async_setup initializes the domain in hass.data
    result = await async_setup(hass, {})

    assert result is True
    assert DOMAIN in hass.data
