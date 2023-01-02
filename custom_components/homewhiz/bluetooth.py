import asyncio
import logging
from typing import Optional

from bleak import BleakClient, BLEDevice
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .homewhiz import Command, HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class HomewhizBluetoothUpdateCoordinator(HomewhizCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
    ) -> None:
        self.address = address
        self._accumulator = MessageAccumulator()
        self._hass = hass
        self._device: BLEDevice | None = None
        self._connection: BleakClient | None = None
        self.alive = True
        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self) -> bool:
        _LOGGER.info(f"Connecting to {self.address}")
        self._device = bluetooth.async_ble_device_from_address(
            self._hass, self.address, connectable=True
        )
        if not self._device:
            raise Exception(f"Device not found for address {self.address}")
        self._connection = await establish_connection(
            client_class=BleakClient,
            device=self._device,
            disconnected_callback=lambda client: self.handle_disconnect(),
            name=self.address,
        )
        if not self._connection.is_connected:
            raise Exception("Can't connect")
        await self._connection.start_notify(
            "0000ac02-0000-1000-8000-00805f9b34fb",
            lambda sender, message: self.hass.create_task(self.handle_notify(message)),
        )
        await self._connection.write_gatt_char(
            "0000ac01-0000-1000-8000-00805f9b34fb",
            bytearray.fromhex("02 04 00 04 00 1a 01 03"),
            response=False,
        )
        _LOGGER.info(f"Successfully connected. RSSI: {self._device.rssi}")

        return True

    async def try_reconnect(self) -> None:
        while self.alive and (
            self._connection is None or not self._connection.is_connected
        ):
            if not bluetooth.async_address_present(
                self.hass, self.address, connectable=True
            ):
                _LOGGER.info(
                    "Device not found. "
                    "Will reconnect automatically when the device becomes available"
                )
                return
            try:
                await self.connect()
            except Exception:
                _LOGGER.info("Can't reconnect. Waiting a minute to try again")
                await asyncio.sleep(60)

    @callback
    def handle_disconnect(self) -> None:
        self._device = None
        self._connection = None
        self.async_set_updated_data(None)
        _LOGGER.info(f"[{self.address}] Disconnected")
        self.hass.create_task(self.try_reconnect())

    @callback
    async def handle_notify(self, message: bytearray) -> None:
        _LOGGER.debug(f"Message received: {message}")
        if len(message) < 10:
            _LOGGER.debug("Ignoring short message")
            return
        full_message = self._accumulator.accumulate_message(message)
        if full_message is not None:
            _LOGGER.debug(
                f"Full message: {full_message}",
            )
            self.async_set_updated_data(full_message)

    async def send_command(self, command: Command) -> None:
        _LOGGER.debug(f"Sending command {command.index}:{command.value}")
        payload = bytearray([2, 4, 0, 4, 0, command.index, 1, command.value])
        assert self._connection is not None
        await self._connection.write_gatt_char(
            "0000ac01-0000-1000-8000-00805F9B34FB",
            payload,
        )

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected

    async def kill(self) -> None:
        self.alive = False
        if self._connection is not None:
            await self._connection.disconnect()


class MessageAccumulator:
    expected_index = 0
    accumulated: bytearray = bytearray()

    def accumulate_message(self, message: bytearray) -> Optional[bytearray]:
        message_index = message[4]
        _LOGGER.debug("Message index: %d", message_index)
        if message_index == 0:
            self.accumulated = message[7:]
            self.expected_index = 1
        elif self.expected_index == 1:
            full_message = self.accumulated + message[7:]
            self.expected_index = 0
            return full_message
        return None
