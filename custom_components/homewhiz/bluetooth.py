import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from bleak import BleakClient, BLEDevice
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_point_in_time

from .const import DOMAIN
from .homewhiz import Command, HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class MessageAccumulator:
    def __init__(self) -> None:
        self._expected_index = 0
        self._accumulated: bytearray = bytearray()

    def accumulate_message(self, message: bytearray) -> bytearray | None:
        message_index = message[4]
        _LOGGER.debug("Message index: %d", message_index)
        if message_index == 0:
            self._accumulated = message[7:]
            self._expected_index = 1
        elif message_index == 1 and self._expected_index == 1:
            full_message = self._accumulated + message[7:]
            self._expected_index = 0
            return full_message
        else:
            # Unexpected sequence: reset to avoid getting permanently stuck
            _LOGGER.warning(
                "Unexpected message index %d, resetting accumulator", message_index
            )
            self._expected_index = 0
            self._accumulated = bytearray()
        return None


class HomewhizBluetoothUpdateCoordinator(HomewhizCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        reconnect_interval: int | None = None,
    ) -> None:
        self.address = address
        self._accumulator = MessageAccumulator()
        self._hass = hass
        self._device: BLEDevice | None = None
        self._device_lock = asyncio.Lock()
        self._connection: BleakClient | None = None
        self._connection_lock = asyncio.Lock()
        self.alive = True
        # To ensure that only one reconnect is performed at a time
        self.reconnecting_lock = asyncio.Lock()
        # Allow users to configure regular Bluetooth reconnections
        self._reconnect_interval: int | None = reconnect_interval
        self._reconnect_interval_task: None | Callable = None
        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self) -> bool:
        if self.is_connected:
            _LOGGER.debug("Already connected, skipping connect()")
            return True
        async with self._connection_lock:
            if self.is_connected:  # double-checked locking
                _LOGGER.debug("Already connected, skipping connect()")
                return True
            _LOGGER.info("Connecting to %s", self.address)
            async with self._device_lock:
                self._device = bluetooth.async_ble_device_from_address(
                    self._hass, self.address, connectable=True
                )
                # Self connection should be None
                if self._connection:
                    _LOGGER.warning(
                        "Trying to connect even though connection already exists!"
                    )
                if not self._device:
                    raise RuntimeError(f"Device not found for address {self.address}")

                # How to clear disconnected_callback?
                _LOGGER.debug("Establishing connection")
                self._connection = await establish_connection(
                    client_class=BleakClient,
                    device=self._device,
                    disconnected_callback=self.disconnected_callback,
                    name=self.address,
                )

            def _raise_cant_connect() -> None:
                msg = "Can't connect"
                raise RuntimeError(msg)

            try:
                if not self._connection.is_connected:
                    _raise_cant_connect()

                await asyncio.sleep(0.5)

                _LOGGER.debug("Starting notify")
                await self._connection.start_notify(
                    "0000ac02-0000-1000-8000-00805f9b34fb",
                    lambda sender, message: self.hass.create_task(
                        self.handle_notify(message)
                    ),
                )
                _LOGGER.debug("Sending initial command")
                await self._connection.write_gatt_char(
                    "0000ac01-0000-1000-8000-00805f9b34fb",
                    bytearray.fromhex("02 04 00 04 00 1a 01 03"),
                    response=False,
                )
            except Exception:
                # WARNING, not ERROR: this failure is transient and the
                # reconnect loop takes over; a persistent problem still
                # surfaces as ERROR via "Can't reconnect" every 30s.
                _LOGGER.warning(
                    "Failed to set up connection, cleaning up", exc_info=True
                )
                with contextlib.suppress(Exception):
                    await self._connection.disconnect()
                self._connection = None  # ensure clean state for next attempt
                raise

        # To retrieve RSSI value
        # https://developers.home-assistant.io/docs/core/bluetooth/api/#fetching-the-latest-bluetoothserviceinfobleak-for-a-device
        _LOGGER.debug("Fetching service info")
        service_info = bluetooth.async_last_service_info(
            self.hass, self.address, connectable=True
        )
        if service_info is not None:
            _LOGGER.info("Successfully connected. RSSI: %s", service_info.rssi)
        else:
            _LOGGER.info("Successfully connected (RSSI not available)")

        # If reconnection is configured, set a task to reconnect after interval
        if self._reconnect_interval:
            self.create_reconnect_interval_task()
        else:
            _LOGGER.debug("Reconnect after interval task not set")

        return True

    def create_reconnect_interval_task(self) -> None:
        # Cancel any existing task
        if self._reconnect_interval_task:
            _LOGGER.debug(
                "Existing reconnect after %s hours task cancelled",
                self._reconnect_interval,
            )
            self._reconnect_interval_task()

        if not self._reconnect_interval:
            return

        self._reconnect_interval_task = async_track_point_in_time(
            hass=self.hass,
            action=self.reconnect_callback,
            point_in_time=datetime.now()
            + timedelta(hours=float(self._reconnect_interval)),
        )
        _LOGGER.debug("Reconnect after %s hours task set", self._reconnect_interval)

    @callback
    def disconnected_callback(self, client: BleakClient | None = None) -> None:
        _LOGGER.debug("Disconnected callback")
        # Prevent locking when home assistant is shutting down
        if not self.alive:
            _LOGGER.debug("Disconnected callback called but not alive")
            return
        self.hass.create_task(self.handle_disconnect(client))

    @callback
    def reconnect_callback(self, *args: Any) -> None:
        # Trigger a disconnect, the disconnected_callback will trigger the reconnect
        _LOGGER.debug("Reconnect callback")
        if self.alive:
            connection = self._connection  # capture a local reference atomically
            if connection is not None:
                self.hass.create_task(connection.disconnect())

    async def try_reconnect(self) -> None:
        async with self.reconnecting_lock:
            _LOGGER.debug("[%s] Trying to reconnect", self.address)
            while self.alive and not self.is_connected:
                if not bluetooth.async_address_present(
                    self.hass, self.address, connectable=True
                ):
                    _LOGGER.info(
                        "Device not found. "
                        "Will reconnect automatically when the device becomes available"
                    )
                    await asyncio.sleep(60)
                    continue  # instead of return
                try:
                    _LOGGER.debug(
                        "[%s] Establish connection from reconnect",
                        self.address,
                    )
                    await self.connect()
                    # Reconnect was successful!
                    _LOGGER.debug("Reconnecting was successful!")
                except Exception:
                    _LOGGER.exception(
                        "Can't reconnect. Waiting 30 seconds to try again"
                    )
                    await asyncio.sleep(30)

    async def handle_disconnect(
        self, client: BleakClient | None = None, *args: Any
    ) -> None:
        _LOGGER.debug("Handling disconnect%s...", " by time interval" if args else "")
        async with self._connection_lock:
            # Only a disconnect of the live connection may tear it down.
            # A late callback from a superseded client would otherwise kill
            # a fresh, healthy connection established in the meantime.
            if (
                client is not None
                and self._connection is not None
                and client is not self._connection
            ):
                _LOGGER.debug("Ignoring disconnect from a stale connection")
                return
            async with self._device_lock:
                self._device = None
            # Ensure device is disconnected
            if self._connection:
                _LOGGER.info("Triggering disconnect")
                with contextlib.suppress(Exception):
                    await self._connection.disconnect()
            self.hass.add_job(self.async_set_updated_data, None)
            self._connection = None
        # Spawn the task AFTER releasing the lock
        _LOGGER.info("[%s] Disconnected", self.address)
        self.hass.create_task(self.try_reconnect())

    # @callback removed – the function is invoked via create_task, not called directly
    async def handle_notify(self, message: bytearray) -> None:
        _LOGGER.debug("Message received: %s", message)
        if len(message) < 10:
            _LOGGER.debug("Ignoring short message")
            return
        full_message = self._accumulator.accumulate_message(message)
        if full_message is not None:
            _LOGGER.debug(
                "Full message: %s",
                full_message,
            )
            self.async_set_updated_data(full_message)

    async def send_command(self, command: Command) -> None:
        _LOGGER.debug("Sending command %s:%s", command.index, command.value)
        async with self._connection_lock:
            if self._connection is None or not self._connection.is_connected:
                _LOGGER.warning("Cannot send command: not connected")
                raise HomeAssistantError("Device not connected")
            payload = bytearray([2, 4, 0, 4, 0, command.index, 1, command.value])
            try:
                await self._connection.write_gatt_char(
                    "0000ac01-0000-1000-8000-00805F9B34FB",
                    payload,
                )
            except Exception as e:
                _LOGGER.error("Failed to send command: %s", e)
                raise
            _LOGGER.debug("Command sent")

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected

    async def kill(self) -> None:
        _LOGGER.debug("[%s] Killing connection", self.address)
        self.alive = False  # set FIRST, before calling disconnect()
        async with self._connection_lock:
            if self._connection is not None:
                with contextlib.suppress(Exception):
                    await self._connection.disconnect()
            if self._reconnect_interval_task:
                self._reconnect_interval_task()
            _LOGGER.debug("[%s] Connection killed", self.address)
