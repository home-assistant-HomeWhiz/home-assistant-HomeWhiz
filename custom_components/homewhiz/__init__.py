import asyncio
import logging

from dacite import from_dict
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.requirements import RequirementsNotFound
from homeassistant.util.package import install_package, is_installed

from .api import IdExchangeResponse
from .bluetooth import HomewhizBluetoothUpdateCoordinator
from .cloud import HomewhizCloudUpdateCoordinator
from .config_flow import CloudConfig
from .const import DOMAIN, PLATFORMS

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(f"Setting up entry {entry.unique_id}")
    address = entry.unique_id
    if "ids" not in entry.data:
        raise Exception(
            "Appliance config not fetched from the API. "
            "Please configure the integration again"
        )
    if entry.data["cloud_config"] is not None:
        return await setup_cloud(entry, hass)
    else:
        return await setup_bluetooth(address, entry, hass)


async def setup_bluetooth(
    address: str | None, entry: ConfigEntry, hass: HomeAssistant
) -> bool:
    _LOGGER.info("Setting up bluetooth connection")

    if not entry.unique_id:
        return False

    coordinator = hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = HomewhizBluetoothUpdateCoordinator(hass, entry.unique_id)

    @callback
    def connect(
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        hass.async_create_task(coordinator.connect())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        async_register_callback(
            hass,
            connect,
            BluetoothCallbackMatcher(address=address),  # type: ignore[typeddict-item]
            BluetoothScanningMode.ACTIVE,
        )
    )

    # Set up listening to shutdown event
    def disconnect_service(_event) -> None:  # type: ignore
        _LOGGER.debug("Received shutdown event and triggering kill")
        hass.create_task(coordinator.kill())

    _LOGGER.debug("Setting up shutdown event listener")
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, disconnect_service)

    return True


def _lazy_install_awsiotsdk() -> None:
    custom_required_packages = ["awsiotsdk"]
    for pkg in custom_required_packages:
        if not is_installed(pkg) and not install_package(pkg):
            raise RequirementsNotFound(DOMAIN, [pkg])


async def setup_cloud(entry: ConfigEntry, hass: HomeAssistant) -> bool:
    _LOGGER.info("Setting up cloud connection")

    loop = asyncio.get_event_loop()
    lazy_install_awsiotsdk_task = loop.run_in_executor(None, _lazy_install_awsiotsdk)
    await lazy_install_awsiotsdk_task

    ids = from_dict(IdExchangeResponse, entry.data["ids"])
    cloud_config = from_dict(CloudConfig, entry.data["cloud_config"])
    coordinator = hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = HomewhizCloudUpdateCoordinator(hass, ids.appId, cloud_config, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_task(hass, coordinator.connect())
    _LOGGER.info("Setup cloud connection successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(f"Unloading entry {entry.unique_id}")
    await hass.data[DOMAIN][entry.entry_id].kill()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
