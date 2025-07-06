"""Global fixtures for Home Assistant EasyLog Cloud integration."""
from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


# This fixture, when used, will result in calls to async_get_data to return None. To have the call
# return a value, we would add the `return_value=<VALUE_TO_RETURN>` parameter to the patch call.
@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from API."""
    with patch("custom_components.ha_easylog_cloud.HAEasylogCloudApiClient.async_get_devices_data"):
        yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate error when retrieving data from API."""
    with patch(
        "custom_components.ha_easylog_cloud.HAEasylogCloudApiClient.async_get_devices_data",
        side_effect=Exception,
    ):
        yield


@pytest.fixture(name="mock_hass_aiohttp", autouse=True)
async def mock_hass_aiohttp_fixture():
    """Mock Home Assistant aiohttp client session globally.

    Many unit-tests instantiate the API / coordinator directly which internally calls
    ``async_get_clientsession`` at import time (i.e. outside of an event-loop).  To
    avoid warnings like *"The object should be created within an async function"*
    we replace the helper with an ``AsyncMock`` returning a dummy session for the
    entire test run.
    """
    from unittest.mock import AsyncMock, patch

    async_mock_session = AsyncMock()

    with patch("custom_components.ha_easylog_cloud.api.async_get_clientsession", return_value=async_mock_session):
        yield


@pytest.fixture(name="mock_hass_loader", autouse=True)
async def mock_hass_loader_fixture():
    """Prevent IntegrationNotFound errors when Home Assistant looks up metadata.

    The config-flow helper ``async_get_integration`` expects the integration to be
    discoverable via Home Assistant's loader.  We stub this call so the config
    flow under test does not depend on the actual manifest on disk.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_integration = MagicMock()
    mock_integration.single_config_entry = False

    with patch("homeassistant.loader.async_get_integration", new=AsyncMock(return_value=mock_integration)):
        yield
