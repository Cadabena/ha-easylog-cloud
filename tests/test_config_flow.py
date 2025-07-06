"""Tests for the EasylogCloud config flow."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_easylog_cloud.config_flow import EasylogCloudConfigFlow
from custom_components.ha_easylog_cloud.const import CONF_PASSWORD
from custom_components.ha_easylog_cloud.const import CONF_USERNAME
from custom_components.ha_easylog_cloud.const import DOMAIN


async def test_flow_user(hass: HomeAssistant) -> None:
    """Test user initiated config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_flow_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test user initiated config flow with invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock the API client to fail authentication
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
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
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            return_value=[{"id": 1, "name": "Test Device"}]
        )
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
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            return_value=[{"id": 1, "name": "Test Device"}]
        )
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
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
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
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(
            side_effect=Exception("Fetch failed")
        )
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
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(
            side_effect=Exception("Extract failed")
        )
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
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            side_effect=Exception("Extract failed")
        )
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_test_credentials_success(hass):
    """Test _test_credentials method with success."""
    flow = EasylogCloudConfigFlow()
    flow.hass = hass

    # Mock the API client to succeed
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            return_value=[{"id": 1, "name": "Test Device"}]
        )
        mock_instance.account_name = "test_user"
        mock_api.return_value = mock_instance

        valid, name = await flow._test_credentials("test@example.com", "test-pass")

    assert valid is True
    assert name == "test_user"


async def test_test_credentials_success_no_account_name(hass):
    """Test _test_credentials method with success but no account name."""
    flow = EasylogCloudConfigFlow()
    flow.hass = hass

    # Mock the API client to succeed but no account name
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            return_value=[{"id": 1, "name": "Test Device"}]
        )
        mock_instance.account_name = None
        mock_api.return_value = mock_instance

        valid, name = await flow._test_credentials("test@example.com", "test-pass")

    assert valid is True
    assert name is None


async def test_test_credentials_failure(hass):
    """Test _test_credentials method with failure."""
    flow = EasylogCloudConfigFlow()
    flow.hass = hass

    # Mock the API client to fail
    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
        mock_api.return_value = mock_instance

        valid, name = await flow._test_credentials("test@example.com", "test-pass")

    assert valid is False
    assert name is None


async def test_show_form(hass: HomeAssistant) -> None:
    """Test _show_config_form method."""
    flow = EasylogCloudConfigFlow()
    flow.hass = hass
    flow._errors = {"base": "auth"}

    result = await flow._show_config_form({CONF_USERNAME: "test@example.com"})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "auth"}


async def test_flow_with_valid_credentials(hass: HomeAssistant) -> None:
    """Test complete flow with valid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            return_value=[{"id": 1, "name": "Test Device"}]
        )
        mock_instance.account_name = "test_user"
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test_user"


async def test_flow_with_invalid_credentials(hass: HomeAssistant) -> None:
    """Test complete flow with invalid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_flow_with_no_account_name(hass: HomeAssistant) -> None:
    """Test complete flow with no account name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            return_value=[{"id": 1, "name": "Test Device"}]
        )
        mock_instance.account_name = None
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test@example.com"


async def test_flow_with_no_devices(hass: HomeAssistant) -> None:
    """Test complete flow with no devices."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
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


async def test_flow_with_fetch_devices_failure(hass: HomeAssistant) -> None:
    """Test complete flow with fetch_devices_page failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(
            side_effect=Exception("Fetch failed")
        )
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_flow_with_extract_devices_failure(hass: HomeAssistant) -> None:
    """Test complete flow with extract_devices_arr_from_html failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(
            side_effect=Exception("Extract failed")
        )
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_flow_with_extract_device_list_failure(hass: HomeAssistant) -> None:
    """Test complete flow with extract_device_list failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_easylog_cloud.config_flow.HAEasylogCloudApiClient"
    ) as mock_api:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock()
        mock_instance.fetch_devices_page = AsyncMock(return_value="<html></html>")
        mock_instance._extract_devices_arr_from_html = MagicMock(return_value="test")
        mock_instance._extract_device_list = MagicMock(
            side_effect=Exception("Extract failed")
        )
        mock_api.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test-pass"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}
