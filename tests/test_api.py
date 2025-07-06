"""Tests for Home Assistant EasyLog Cloud api."""
import asyncio

import aiohttp
from custom_components.ha_easylog_cloud.api import (
    HAEasylogCloudApiClient,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def test_api(hass, aioclient_mock, caplog):
    """Test API calls."""

    # To test the api submodule, we first create an instance of our API client
    api = HAEasylogCloudApiClient(hass, "test", "test")

    # Test the stub methods
    assert await api.async_set_title("test") is None
    assert await api.api_wrapper("get", "https://example.com") is None

    # Test that the API client can be instantiated
    assert api._username == "test"
    assert api._password == "test"
    assert api._session is not None
