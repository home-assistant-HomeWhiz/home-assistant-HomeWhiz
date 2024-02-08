import asyncio
import logging

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
        # To ensure that only one reconnect is performed at a time
        self._reconnecting = False
        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self) -> bool:
        _LOGGER.info(f"Connecting to {self.address}")
        self._device = bluetooth.async_ble_device_from_address(
            self._hass, self.address, connectable=True
        )
        # Self connection should be None
        if self._connection:
            _LOGGER.warning("Trying to connect even though connection already exists!")
        if not self._device:
            raise Exception(f"Device not found for address {self.address}")

        # How to clear disconnected_callback?
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

        # To retrieve RSSI value
        # https://developers.home-assistant.io/docs/core/bluetooth/api/#fetching-the-latest-bluetoothserviceinfobleak-for-a-device
        service_info = bluetooth.async_last_service_info(
            self.hass, self.address, connectable=True
        )
        assert service_info is not None
        _LOGGER.info(f"Successfully connected. RSSI: {service_info.rssi}")

        return True

    async def try_reconnect(self) -> None:
        _LOGGER.debug(f"[{self.address}] Trying to reconnect")
        if self._reconnecting:
            _LOGGER.warning("Stopping reconnect as reconnect is already in progress")
        while self.alive and not self.is_connected:
            self._reconnecting = True
            if not bluetooth.async_address_present(
                self.hass, self.address, connectable=True
            ):
                _LOGGER.info(
                    "Device not found. "
                    "Will reconnect automatically when the device becomes available"
                )
                return
            try:
                _LOGGER.debug(f"[{self.address}] Establish connection from reconnect")
                await self.connect()
                # Reconnect was successful!
                _LOGGER.debug("Reconnecting was successful!")
                self._reconnecting = False
            except Exception:
                _LOGGER.exception("Can't reconnect. Waiting 30 seconds to try again")
                await asyncio.sleep(30)

    @callback
    def handle_disconnect(self) -> None:
        _LOGGER.debug("Hanndling disconnect...")
        self._device = None
        # Ensure device is disconnected
        if self._connection:
            _LOGGER.info("Triggering disconnect")
            self.hass.create_task(self._connection.disconnect())
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
        _LOGGER.debug("Command sent")

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected

    async def kill(self) -> None:
        _LOGGER.debug(f"[{self.address}] Killing connection")
        self.alive = False
        if self._connection is not None:
            await self._connection.disconnect()
        _LOGGER.debug(f"[{self.address}] Connection killed")


class MessageAccumulator:
    expected_index = 0
    accumulated: bytearray = bytearray()

    def accumulate_message(self, message: bytearray) -> bytearray | None:
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
