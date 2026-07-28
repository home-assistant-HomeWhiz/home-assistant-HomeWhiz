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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.requirements import RequirementsNotFound
from homeassistant.util.package import install_package, is_installed

from .api import IdExchangeResponse
from .appliance_controls import forget_controls
from .bluetooth import HomewhizBluetoothUpdateCoordinator
from .cloud import HomewhizCloudUpdateCoordinator
from .config_flow import CloudConfig
from .const import CONF_BT_RECONNECT_INTERVAL, DOMAIN, PLATFORMS

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Setting up entry %s", entry.unique_id)
    address = entry.unique_id
    if "ids" not in entry.data:
        raise HomeAssistantError(
            "Appliance config not fetched from the API. "
            "Please configure the integration again"
        )
    if entry.data["cloud_config"] is not None:
        return await setup_cloud(entry, hass)
    return await setup_bluetooth(address, entry, hass)


async def setup_bluetooth(
    address: str | None, entry: ConfigEntry, hass: HomeAssistant
) -> bool:
    _LOGGER.info("Setting up bluetooth connection")

    if not entry.unique_id:
        _LOGGER.info("No unique entry id")
        return False

    coordinator = hass.data.setdefault(DOMAIN, {})[entry.entry_id] = (
        HomewhizBluetoothUpdateCoordinator(
            hass, entry.unique_id, entry.options.get(CONF_BT_RECONNECT_INTERVAL)
        )
    )

    async def connect_retrieving_errors() -> None:
        # Heals on the next advertisement, not via try_reconnect() (that
        # only runs after a disconnect from an established connection).
        try:
            await coordinator.connect()
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Connect from advertisement failed, waiting for the next advertisement"
            )

    @callback
    def connect(
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        coordinator.note_advertisement()
        if not coordinator.is_connected and not coordinator.reconnecting_lock.locked():
            _LOGGER.debug("Called connect callback in setup_bluetooth")
            hass.async_create_task(connect_retrieving_errors())

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
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, disconnect_service)
    )

    return True


def _lazy_install_awsiotsdk() -> None:
    custom_required_packages = ["awsiotsdk"]
    for pkg in custom_required_packages:
        if not is_installed(pkg) and not install_package(pkg):
            raise RequirementsNotFound(DOMAIN, [pkg])


async def setup_cloud(entry: ConfigEntry, hass: HomeAssistant) -> bool:
    _LOGGER.info("Setting up cloud connection")

    loop = asyncio.get_running_loop()
    lazy_install_awsiotsdk_task = loop.run_in_executor(None, _lazy_install_awsiotsdk)
    await lazy_install_awsiotsdk_task

    ids = from_dict(IdExchangeResponse, entry.data["ids"])
    cloud_config = from_dict(CloudConfig, entry.data["cloud_config"])
    coordinator = hass.data.setdefault(DOMAIN, {})[entry.entry_id] = (
        HomewhizCloudUpdateCoordinator(hass, ids.appId, cloud_config, entry)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_task(hass, coordinator.connect())
    _LOGGER.info("Setup cloud connection successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Unloading entry %s", entry.unique_id)
    await hass.data[DOMAIN][entry.entry_id].kill()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        forget_controls(entry.entry_id)
    return unload_ok
