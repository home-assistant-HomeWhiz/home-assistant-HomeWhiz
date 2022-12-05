import json
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import DOMAIN
from .api import (
    login,
    LoginError,
    make_api_get_request,
    make_id_exchange_request,
    make_get_config_request,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class TiltConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeWhiz"""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}
        self._address: str | None = None
        self._name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not discovery_info.name.startswith("HwZ"):
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        self._address = discovery_info.address
        self._name = discovery_info.name
        return await self.async_step_credentials()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            self._address = address
            self._name = self._discovered_devices[address]
            return await self.async_step_credentials()

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            if discovery_info.name.startswith("HwZ"):
                self._discovered_devices[address] = discovery_info.name

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Handle the user step to provide HomeWhiz credentials.
        Credentials are used to fetch appliance config
        """
        errors = {}
        if user_input is not None:
            assert self._address is not None
            assert self._name is not None
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                credentials = await login(username, password)
                id_response = await make_id_exchange_request(self._name)
                appId = id_response["appId"]
                modelId = id_response["m"]
                contents_response = await make_api_get_request(
                    host="api.arcelikiot.com",
                    canonical_uri="/procam/contents",
                    canonical_querystring=(
                        f"applianceId={appId}&ctype=CONFIGURATION&lang=en-GB&testMode=true"
                    ),
                    credentials=credentials,
                )
                contents = contents_response["data"]["results"][0]
                config_response = await make_get_config_request(contents)
                _LOGGER.debug(json.dumps(config_response, indent=4))
                return self.async_create_entry(
                    title=self._name,
                    data={"config": config_response, "model_id": modelId},
                )
            except LoginError:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.PASSWORD,
                        )
                    ),
                },
            ),
            errors=errors,
        )
