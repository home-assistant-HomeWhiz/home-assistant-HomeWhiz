import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.loader import async_get_custom_components

from .const import DOMAIN, COORDINATORS
from .homewhiz import ScannerHelper, MessageAccumulator, parse_message, WasherState

_LOGGER: logging.Logger = logging.getLogger(__package__)
CONNECTION_RETRY_TIMEOUT = 30


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info("Start scanning")
    scanner = ScannerHelper()
    devices = await scanner.scan(hass)
    _LOGGER.info("Found {} device(s)".format(len(devices)))
    hass.data[DOMAIN].setdefault(COORDINATORS, [])
    for device in devices:
        coordinator = HomewhizDataUpdateCoordinator(hass, device)
        hass.data[DOMAIN][COORDINATORS].append(coordinator)
        hass.create_task(coordinator.connect())

    await async_get_custom_components(hass)
    hass.config_entries.async_setup_platforms(entry, [Platform.SENSOR])
    return True


class HomewhizDataUpdateCoordinator(DataUpdateCoordinator[WasherState]):
    def __init__(
        self,
        hass: HomeAssistant,
        device: BLEDevice,
    ) -> None:
        self._device = device
        self.client = BleakClient(device)
        self.accumulator = MessageAccumulator()
        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self):
        await self.connect_internal()
        self.client.set_disconnected_callback(
            lambda client: self.hass.create_task(self.reconnect(client))
        )
        await self.start_listening()
        return True

    async def start_listening(self):
        await self.client.start_notify(
            "0000ac02-0000-1000-8000-00805f9b34fb",
            lambda sender, message: self.hass.create_task(
                self.handle_notify(sender, message)
            ),
        )
        await self.client.write_gatt_char(
            "0000ac01-0000-1000-8000-00805f9b34fb",
            bytearray.fromhex("02 04 00 04 00 1a 01 03"),
            response=False,
        )

    @callback
    async def handle_notify(self, sender: int, message: bytearray):
        _LOGGER.debug(f"message {message}")
        if len(message) < 10:
            return
        full_message = self.accumulator.accumulate_message(message)
        if full_message is not None:
            data = parse_message(full_message)
            _LOGGER.debug(f"data {data}")
            self.async_set_updated_data(data)

    @callback
    async def reconnect(self, client: BleakClient):
        _LOGGER.debug("Disconnected, reconnecting")
        await self.connect_internal()
        await self.client.stop_notify("0000ac02-0000-1000-8000-00805f9b34fb")
        await self.start_listening()

    async def connect_internal(self):
        while not self.client.is_connected:
            _LOGGER.debug("Trying to connect")
            try:
                await self.client.connect()
                _LOGGER.debug("connected")
            except Exception as e:
                _LOGGER.warning(e)
                await asyncio.sleep(CONNECTION_RETRY_TIMEOUT)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(COORDINATORS, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
