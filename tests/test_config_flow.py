"""Tests for the EasylogCloud config flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_easylog_cloud.const import DOMAIN, CONF_USERNAME, CONF_PASSWORD


async def test_flow_user(hass: HomeAssistant) -> None:
    """Test user initiated config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    expected = {
        "data_schema": {
            CONF_USERNAME: str,
            CONF_PASSWORD: str,
        },
        "description_placeholders": None,
        "errors": {},
        "flow_id": result["flow_id"],
        "handler": DOMAIN,
        "last_step": None,
        "step_id": "user",
        "type": "form",
    }

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_flow_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test user initiated config flow with invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client to fail authentication
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_flow_user_valid_auth(hass: HomeAssistant) -> None:
    """Test user initiated config flow with valid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client to succeed
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
        mock_instance.account_name = "test_user"
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test_user"
    assert result2["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test-pass",
    }


async def test_flow_user_no_account_name(hass: HomeAssistant) -> None:
    """Test user initiated config flow with no account name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client to succeed but no account name
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
        mock_instance.account_name = None
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test@example.com"  # Should fallback to email
    assert result2["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test-pass",
    }


async def test_flow_user_no_devices(hass: HomeAssistant) -> None:
    """Test user initiated config flow with no devices."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client to succeed but no devices
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="")
        mock_instance._extract_device_list = MagicMock(return_value=[])
        mock_instance.account_name = "test_user"
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test_user"
    assert result2["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test-pass",
    }


async def test_flow_user_fetch_devices_failure(hass: HomeAssistant) -> None:
    """Test user initiated config flow with fetch_devices_page failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client with fetch_devices_page failure
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(side_effect=Exception("Fetch failed"))
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_flow_user_extract_devices_failure(hass: HomeAssistant) -> None:
    """Test user initiated config flow with extract_devices_arr_from_html failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client with extract_devices_arr_from_html failure
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(side_effect=Exception("Extract failed"))
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_flow_user_extract_device_list_failure(hass: HomeAssistant) -> None:
    """Test user initiated config flow with extract_device_list failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client with extract_device_list failure
    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient') as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(side_effect=Exception("Extract list failed"))
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_test_credentials_success(hass):
    """Test successful credential validation."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow

    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass

    # Mock the API client
    mock_api_client = type('MockApiClient', (), {
        'authenticate': AsyncMock(),
        'fetch_devices_page': AsyncMock(return_value="<html></html>"),
        '_extract_devices_arr_from_html': MagicMock(return_value="test"),
        '_extract_device_list': MagicMock(return_value=[{"id": 1, "name": "Test Device"}]),
        'account_name': "test_user"
    })()

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        valid, name = await flow._test_credentials("test_user", "test_pass")

        assert valid is True
        assert name == "test_user"


async def test_test_credentials_success_no_account_name(hass):
    """Test successful credential validation without account name."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow

    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass

    # Mock the API client without account name
    mock_api_client = type('MockApiClient', (), {
        'authenticate': AsyncMock(),
        'fetch_devices_page': AsyncMock(return_value="<html></html>"),
        '_extract_devices_arr_from_html': MagicMock(return_value="test"),
        '_extract_device_list': MagicMock(return_value=[{"id": 1, "name": "Test Device"}]),
        'account_name': None
    })()

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        valid, name = await flow._test_credentials("test_user", "test_pass")

        assert valid is True
        assert name is None


async def test_test_credentials_failure(hass):
    """Test failed credential validation."""
    from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow

    # Create a config flow instance
    flow = EasylogCloudConfigFlow()
    flow.hass = hass

    # Mock the API client to fail
    mock_api_client = type('MockApiClient', (), {
        'authenticate': AsyncMock(side_effect=Exception("Auth failed")),
        'fetch_devices_page': AsyncMock(),
        '_extract_devices_arr_from_html': MagicMock(return_value="test"),
        '_extract_device_list': MagicMock(return_value=[]),
        'account_name': None
    })()

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        valid, name = await flow._test_credentials("test_user", "test_pass")

        assert valid is False
        assert name is None


async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_flow_with_valid_credentials(hass: HomeAssistant) -> None:
    """Test successful config flow with valid credentials."""
    # Mock the API client and its methods
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="test")
    mock_api_client._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
    mock_api_client.account_name = "test_user"

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "test_user"


async def test_flow_with_invalid_credentials(hass: HomeAssistant) -> None:
    """Test config flow with invalid credentials."""
    # Mock the API client to raise exception
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock(side_effect=Exception("Auth failed"))

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "auth"}


async def test_flow_with_no_account_name(hass: HomeAssistant) -> None:
    """Test config flow with no account name returned."""
    # Mock the API client without account name
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="test")
    mock_api_client._extract_device_list = MagicMock(return_value=[{"id": 1, "name": "Test Device"}])
    mock_api_client.account_name = None

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "test@example.com"


async def test_flow_with_no_devices(hass: HomeAssistant) -> None:
    """Test config flow with no devices found."""
    # Mock the API client with no devices
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="")
    mock_api_client._extract_device_list = MagicMock(return_value=[])
    mock_api_client.account_name = "test_user"

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "test_user"


async def test_flow_with_fetch_devices_failure(hass: HomeAssistant) -> None:
    """Test config flow with fetch_devices_page failure."""
    # Mock the API client with fetch_devices_page failure
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(side_effect=Exception("Fetch failed"))

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "auth"}


async def test_flow_with_extract_devices_failure(hass: HomeAssistant) -> None:
    """Test config flow with extract_devices_arr_from_html failure."""
    # Mock the API client with extract_devices_arr_from_html failure
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(side_effect=Exception("Extract failed"))

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "auth"}


async def test_flow_with_extract_device_list_failure(hass: HomeAssistant) -> None:
    """Test config flow with extract_device_list failure."""
    # Mock the API client with extract_device_list failure
    mock_api_client = AsyncMock()
    mock_api_client.authenticate = AsyncMock()
    mock_api_client.fetch_devices_page = AsyncMock(return_value="<html></html>")
    mock_api_client._extract_devices_arr_from_html = MagicMock(return_value="test")
    mock_api_client._extract_device_list = MagicMock(side_effect=Exception("Extract list failed"))

    with patch('custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient', return_value=mock_api_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "auth"}



