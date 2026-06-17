import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from bleak import BleakClient, BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_point_in_time

from .const import DOMAIN
from .homewhiz import Command, HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

# GATT characteristics exposed by HomeWhiz appliances
NOTIFY_CHARACTERISTIC = "0000ac02-0000-1000-8000-00805f9b34fb"
COMMAND_CHARACTERISTIC = "0000ac01-0000-1000-8000-00805f9b34fb"
# Handshake written immediately after subscribing to notifications
INIT_COMMAND = bytearray.fromhex("02 04 00 04 00 1a 01 03")

# HomeWhiz appliances frequently terminate the link within a few hundred
# milliseconds of accepting it - before notifications can be enabled - so the
# subscribe step fails with "Not connected" / a dropped-connection error even
# though establish_connection() succeeded. Retry the whole establish+subscribe
# sequence a handful of times in quick succession before falling back to the
# slower background reconnect loop.
_SETUP_MAX_ATTEMPTS = 4
_SETUP_RETRY_DELAY = 1.0

# ESP32 BLE proxies periodically drop the link with a supervision timeout
# (HCI 0x08) due to WiFi/BLE radio coexistence, even on a strong signal.
# Reconnects usually complete within a couple of seconds, but can occasionally
# take much longer (proxy backhaul hiccups, slow re-advertising, or the reconnect
# backoff). The grace period is deliberately generous - well above the typical
# reconnect time - so those slower recoveries don't surface as a spurious
# "unavailable"; entities only go unavailable once the link has genuinely stayed
# down this long.
_DISCONNECT_GRACE_SECONDS = 60

# A control command may arrive during one of those brief blips (entities stay
# available across them), so wait briefly for the in-flight reconnect before
# giving up, and retry the write if the link drops mid-command.
_COMMAND_CONNECT_TIMEOUT = 20
_COMMAND_MAX_ATTEMPTS = 2

# Backoff for the background reconnect loop (seconds). A short initial delay
# re-grabs the (often single) proxy connection slot before the advertisement
# goes stale; the delay grows on repeated failure up to the cap.
_RECONNECT_INITIAL_DELAY = 3
_RECONNECT_MAX_DELAY = 60
_RECONNECT_ABSENT_DELAY = 30


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
        # Time the live connection was opened (used to log how long each
        # connection is held before it drops).
        self._connected_at: datetime | None = None
        # Debounced availability: stays True across brief reconnect blips, only
        # flips False once the connection has been down for the grace period.
        self._available = False
        self._grace_unsub: Callable | None = None
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
            # A stale (disconnected) client may still be referenced - drop it
            # before opening a fresh connection so we never leak a proxy slot.
            if self._connection is not None:
                _LOGGER.warning(
                    "Trying to connect even though connection already exists!"
                )
                with contextlib.suppress(Exception):
                    await self._connection.disconnect()
                self._connection = None
            try:
                await self._open_connection()
            except Exception:
                _LOGGER.exception("Failed to set up connection, cleaning up")
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

        # Record when the connection opened (for hold-duration logging).
        self._connected_at = datetime.now()

        # Back online: cancel any pending unavailable timer and (re)publish
        # availability to entities.
        self._cancel_grace()
        if not self._available:
            self._available = True
            self.async_update_listeners()

        # If reconnection is configured, set a task to reconnect after interval
        if self._reconnect_interval:
            self.create_reconnect_interval_task()
        else:
            _LOGGER.debug("Reconnect after interval task not set")

        return True

    async def _open_connection(self) -> None:
        """Establish a BLE connection and enable notifications.

        Sets ``self._connection`` to the live client on success. Retries the
        whole establish+subscribe sequence a handful of times because the
        appliance often drops the link before notifications can be enabled; one
        of the rapid retries usually lands in a window where it stays up long
        enough to subscribe. Raises the last error if every attempt fails.
        """
        last_error: Exception | None = None
        for attempt in range(1, _SETUP_MAX_ATTEMPTS + 1):
            async with self._device_lock:
                self._device = bluetooth.async_ble_device_from_address(
                    self._hass, self.address, connectable=True
                )
                if not self._device:
                    raise RuntimeError(f"Device not found for address {self.address}")

                _LOGGER.debug(
                    "Establishing connection (attempt %d/%d)",
                    attempt,
                    _SETUP_MAX_ATTEMPTS,
                )
                connection = await establish_connection(
                    client_class=BleakClient,
                    device=self._device,
                    name=self.address,
                    disconnected_callback=self.disconnected_callback,
                    # Re-fetch the best device/path on each internal retry
                    # instead of reusing a stale BLEDevice.
                    ble_device_callback=lambda: bluetooth.async_ble_device_from_address(
                        self._hass, self.address, connectable=True
                    ),
                )

            try:
                # Subscribe and send the handshake immediately - any idle time
                # here invites the appliance to terminate the connection.
                _LOGGER.debug("Starting notify")
                await connection.start_notify(
                    NOTIFY_CHARACTERISTIC,
                    lambda sender, message: self.hass.create_task(
                        self.handle_notify(message)
                    ),
                )
                _LOGGER.debug("Sending initial command")
                await connection.write_gatt_char(
                    COMMAND_CHARACTERISTIC,
                    INIT_COMMAND,
                    response=False,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                _LOGGER.debug(
                    "Connection setup attempt %d/%d failed: %s",
                    attempt,
                    _SETUP_MAX_ATTEMPTS,
                    error,
                )
                with contextlib.suppress(Exception):
                    await connection.disconnect()
                if attempt < _SETUP_MAX_ATTEMPTS:
                    await asyncio.sleep(_SETUP_RETRY_DELAY)
                continue

            # The link may have dropped during setup; because self._connection
            # wasn't set yet, disconnected_callback would have ignored it as a
            # stale client. Verify it's still up before publishing it - there is
            # no await between this check and the assignment, so the callback
            # cannot fire in the gap. If it died, retry like any other setup
            # failure instead of getting stuck believing we're connected.
            if not connection.is_connected:
                last_error = BleakError("Link dropped during connection setup")
                _LOGGER.debug(
                    "Connection setup attempt %d/%d: link dropped during setup",
                    attempt,
                    _SETUP_MAX_ATTEMPTS,
                )
                with contextlib.suppress(Exception):
                    await connection.disconnect()
                if attempt < _SETUP_MAX_ATTEMPTS:
                    await asyncio.sleep(_SETUP_RETRY_DELAY)
                continue

            # Publish the live connection. A drop from here on is recognised by
            # disconnected_callback (client is self._connection).
            self._connection = connection
            return

        assert last_error is not None
        raise last_error

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
        # Ignore callbacks from intermediate/superseded clients created during
        # connection setup retries - only the live connection should trigger a
        # reconnect.
        if client is not None and client is not self._connection:
            _LOGGER.debug("Ignoring disconnect from a stale connection")
            return
        self.hass.create_task(self.handle_disconnect())

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
            delay = _RECONNECT_INITIAL_DELAY
            while self.alive and not self.is_connected:
                if not bluetooth.async_address_present(
                    self.hass, self.address, connectable=True
                ):
                    _LOGGER.info(
                        "Device not found. "
                        "Will reconnect automatically when the device becomes available"
                    )
                    await asyncio.sleep(_RECONNECT_ABSENT_DELAY)
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
                        "Can't reconnect. Waiting %d seconds to try again", delay
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, _RECONNECT_MAX_DELAY)

    async def handle_disconnect(self, *args: Any) -> None:
        _LOGGER.debug("Handling disconnect%s...", " by time interval" if args else "")
        held_for: float | None = None
        if self._connected_at is not None:
            held_for = (datetime.now() - self._connected_at).total_seconds()
            self._connected_at = None
        async with self._connection_lock:
            async with self._device_lock:
                self._device = None
            # Ensure device is disconnected
            if self._connection:
                _LOGGER.info("Triggering disconnect")
                with contextlib.suppress(Exception):
                    await self._connection.disconnect()
            self._connection = None
        # Don't flap entities unavailable on a brief blip - start the grace
        # timer and let try_reconnect race it. Entities keep their last state
        # until the timer fires (only if we're still down by then).
        if self._available and self._grace_unsub is None:
            self._grace_unsub = async_call_later(
                self.hass, _DISCONNECT_GRACE_SECONDS, self._grace_expired
            )
        # Spawn the task AFTER releasing the lock
        if held_for is not None:
            _LOGGER.info(
                "[%s] Disconnected after %.1fs connected", self.address, held_for
            )
        else:
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

    async def _await_connection(self, timeout: float) -> None:
        """Wait up to ``timeout`` seconds for the link to (re)connect.

        Entities stay available across brief supervision-timeout blips, so a
        command can arrive while a reconnect is in flight. Give the background
        reconnect a chance to land instead of failing immediately. Raises
        HomeAssistantError if the device is still not connected by the deadline.
        """
        if self.is_connected:
            return
        _LOGGER.debug("Command waiting up to %ss for the connection", timeout)
        try:
            async with asyncio.timeout(timeout):
                while not self.is_connected:
                    await asyncio.sleep(0.25)
        except TimeoutError as err:
            raise HomeAssistantError("Device not connected") from err

    async def send_command(self, command: Command) -> None:
        _LOGGER.debug("Sending command %s:%s", command.index, command.value)
        payload = bytearray([2, 4, 0, 4, 0, command.index, 1, command.value])
        last_error: Exception | None = None
        for attempt in range(1, _COMMAND_MAX_ATTEMPTS + 1):
            # Wait (bounded) for a reconnect if we're mid-blip; raises cleanly
            # if the device is genuinely gone.
            await self._await_connection(_COMMAND_CONNECT_TIMEOUT)
            async with self._connection_lock:
                if self._connection is None or not self._connection.is_connected:
                    continue  # dropped again before we got the lock; retry
                try:
                    await self._connection.write_gatt_char(
                        COMMAND_CHARACTERISTIC,
                        payload,
                    )
                except Exception as error:  # noqa: BLE001
                    last_error = error
                    _LOGGER.warning(
                        "Command send attempt %d/%d failed: %s",
                        attempt,
                        _COMMAND_MAX_ATTEMPTS,
                        error,
                    )
                    continue
                _LOGGER.debug("Command sent")
                return
        raise HomeAssistantError("Failed to send command to device") from last_error

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected

    @property
    def available(self) -> bool:
        """Debounced availability - True through brief reconnect blips."""
        return self._available

    def _cancel_grace(self) -> None:
        if self._grace_unsub is not None:
            self._grace_unsub()
            self._grace_unsub = None

    @callback
    def _grace_expired(self, _now: datetime) -> None:
        self._grace_unsub = None
        if not self.is_connected:
            _LOGGER.info(
                "[%s] Still disconnected after %ds grace; marking unavailable",
                self.address,
                _DISCONNECT_GRACE_SECONDS,
            )
            self._available = False
            self.async_set_updated_data(None)

    async def kill(self) -> None:
        _LOGGER.debug("[%s] Killing connection", self.address)
        self.alive = False  # set FIRST, before calling disconnect()
        self._cancel_grace()
        self._available = False
        async with self._connection_lock:
            if self._connection is not None:
                with contextlib.suppress(Exception):
                    await self._connection.disconnect()
            if self._reconnect_interval_task:
                self._reconnect_interval_task()
            _LOGGER.debug("[%s] Connection killed", self.address)
