import logging
from dataclasses import asdict, dataclass
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS, CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    ApplianceContents,
    ApplianceInfo,
    IdExchangeResponse,
    LoginError,
    LoginResponse,
    fetch_appliance_contents,
    fetch_appliance_infos,
    login,
    make_id_exchange_request,
)
from .const import CONF_BT_RECONNECT_INTERVAL, DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass
class CloudConfig:
    username: str
    password: str


@dataclass
class EntryData:
    ids: IdExchangeResponse
    contents: ApplianceContents
    appliance_info: ApplianceInfo | None
    cloud_config: CloudConfig | None


class TiltConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for HomeWhiz"""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_bt_devices: dict[str, str] = {}
        self._bt_address: str | None = None
        self._bt_name: str | None = None
        self._cloud_config: CloudConfig | None = None
        self._cloud_credentials: LoginResponse | None = None
        self._cloud_appliances: list[ApplianceInfo] | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not discovery_info.name.startswith("HwZ"):
            return self.async_abort(reason="not_supported")
        self._bt_address = discovery_info.address
        self._bt_name = discovery_info.name
        return await self.async_step_bluetooth_connect()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user",
            menu_options=["select_bluetooth_device", "provide_cloud_credentials"],
        )

    async def async_step_select_bluetooth_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            self._bt_address = address
            self._bt_name = self._discovered_bt_devices[address]
            return await self.async_step_bluetooth_connect()

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_bt_devices:
                continue
            if discovery_info.name.startswith("HwZ"):
                self._discovered_bt_devices[address] = discovery_info.name

        if len(self._discovered_bt_devices) == 0:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="select_bluetooth_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_bt_devices)}
            ),
        )

    async def async_step_bluetooth_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to provide HomeWhiz credentials.
        Credentials are used to fetch appliance config
        """
        errors = {}
        if user_input is not None:
            assert self._bt_address is not None
            assert self._bt_name is not None
            await self.async_set_unique_id(self._bt_address)
            self._abort_if_unique_id_configured()
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                credentials = await login(username, password)
                id_response = await make_id_exchange_request(self._bt_name)
                contents = await fetch_appliance_contents(
                    credentials, id_response.appId
                )
                appliance_infos = await fetch_appliance_infos(credentials)
                appliance_info = next(
                    (
                        ai
                        for ai in appliance_infos
                        if ai.applianceId == id_response.appId
                    ),
                    None,
                )
                data = EntryData(
                    ids=id_response,
                    contents=contents,
                    appliance_info=appliance_info,
                    cloud_config=None,
                )
                return self.async_create_entry(
                    title=appliance_info.name
                    if appliance_info is not None
                    else self._bt_name,
                    data=asdict(data),
                )
            except LoginError:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="bluetooth_connect",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(  # type: ignore[typeddict-item]
                            type=TextSelectorType.PASSWORD,
                        )
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_provide_cloud_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                credentials = await login(username, password)
                self._cloud_config = CloudConfig(username, password)
                self._cloud_credentials = credentials
                return await self.async_step_select_cloud_device()
            except LoginError:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="provide_cloud_credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(  # type: ignore[typeddict-item]
                            type=TextSelectorType.PASSWORD,
                        )
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_select_cloud_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._cloud_credentials is not None
        if user_input is not None:
            assert self._cloud_appliances is not None
            appliance_id = user_input[CONF_ID]
            await self.async_set_unique_id(appliance_id)
            self._abort_if_unique_id_configured()
            appliance = next(
                a for a in self._cloud_appliances if a.applianceId == appliance_id
            )
            contents = await fetch_appliance_contents(
                self._cloud_credentials, appliance_id
            )
            data = EntryData(
                ids=IdExchangeResponse(appliance_id),
                contents=contents,
                appliance_info=appliance,
                cloud_config=self._cloud_config,
            )
            return self.async_create_entry(
                title=appliance.name,
                data=asdict(data),
            )

        if self._cloud_appliances is None:
            self._cloud_appliances = await fetch_appliance_infos(
                self._cloud_credentials
            )
        if len(self._cloud_appliances) == 0:
            return self.async_abort(reason="no_devices_found")
        options = {
            appliance.applianceId: appliance.name
            for appliance in self._cloud_appliances
            if not appliance.is_bt()
        }

        return self.async_show_form(
            step_id="select_cloud_device",
            data_schema=vol.Schema({vol.Required(CONF_ID): vol.In(options)}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        # Cloud
        if config_entry.data["cloud_config"] is not None:
            return CloudOptionsFlowHandler()
        # Bluetooth
        return BluetoothOptionsFlowHandler()


class CloudOptionsFlowHandler(OptionsFlow):
    def __init__(self) -> None:
        """Initialize options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )


class BluetoothOptionsFlowHandler(OptionsFlow):
    def __init__(self) -> None:
        """Initialize options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug("Reloading entries after updating options: %s", user_input)
            self.hass.config_entries.async_update_entry(
                self._config_entry, options=user_input
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_BT_RECONNECT_INTERVAL,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_BT_RECONNECT_INTERVAL, None
                            )
                        },
                    ): cv.positive_int,
                }
            ),
        )
