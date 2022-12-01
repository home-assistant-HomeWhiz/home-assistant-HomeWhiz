import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PLATFORMS
from .homewhiz import MessageAccumulator, ScannerHelper, WasherState, parse_message

_LOGGER: logging.Logger = logging.getLogger(__package__)
CONNECTION_RETRY_TIMEOUT = 30


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    address = entry.unique_id
    coordinator = hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = HomewhizDataUpdateCoordinator(hass, address)

    @callback
    def connect(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        hass.async_create_task(coordinator.connect())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            connect,
            BluetoothCallbackMatcher(address=address),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    return True


class HomewhizDataUpdateCoordinator(DataUpdateCoordinator[WasherState | None]):
    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
    ) -> None:
        self.address = address
        self._accumulator = MessageAccumulator()
        self._hass = hass
        self._conn: BleakClient | None = None
        self.device: BLEDevice | None = None
        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self):
        self.device = bluetooth.async_ble_device_from_address(
            self._hass, self.address, connectable=True
        )
        if not self.device:
            raise Exception(f"Device not found for address {self.address}")
        self._conn = await establish_connection(
            client_class=BleakClient,
            device=self.device,
            disconnected_callback=lambda client: self.handle_disconnect(),
            name=self.address,
        )
        if not self._conn.is_connected:
            raise Exception(f"Can't connect to ${self.address}")
        await self._conn.start_notify(
            "0000ac02-0000-1000-8000-00805f9b34fb",
            lambda sender, message: self.hass.create_task(
                self.handle_notify(sender, message)
            ),
        )
        await self._conn.write_gatt_char(
            "0000ac01-0000-1000-8000-00805f9b34fb",
            bytearray.fromhex("02 04 00 04 00 1a 01 03"),
            response=False,
        )
        _LOGGER.info(f"[{self.address}] Successfully connected")

        return True

    @callback
    def handle_disconnect(self):
        self.device = None
        self.async_set_updated_data(None)
        _LOGGER.info(f"[{self.address}] Disconnected")

    @callback
    async def handle_notify(self, sender: int, message: bytearray):
        _LOGGER.debug(f"[{self.address}] Message received: {message}")
        if len(message) < 10:
            _LOGGER.debug(f"[{self.address}] Message too short, ignoring")
            return
        full_message = self._accumulator.accumulate_message(message)
        if full_message is not None:
            data = parse_message(full_message)
            _LOGGER.debug(f"[{self.address}] Parsed message: {data}")
            self.async_set_updated_data(data)

    async def disconnect(self):
        await self._conn.disconnect()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.data[DOMAIN][entry.entry_id].disconnect()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
