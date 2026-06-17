"""Unit tests for the Bluetooth coordinator's resilience logic.

These exercise the connection-blip handling added to fix the flapping reported
in issue #367: the availability debounce and the send_command wait/retry. They
build the coordinator without running DataUpdateCoordinator.__init__ (no running
Home Assistant needed) and mock the BleakClient.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.homewhiz import bluetooth as bt
from custom_components.homewhiz.bluetooth import (
    COMMAND_CHARACTERISTIC,
    HomewhizBluetoothUpdateCoordinator,
    MessageAccumulator,
)
from custom_components.homewhiz.homewhiz import Command


class _FakeConnection:
    """Minimal stand-in for a connected BleakClient."""

    def __init__(self, *, connected: bool = True, write_side_effect=None) -> None:
        self.is_connected = connected
        self.write_gatt_char = AsyncMock(side_effect=write_side_effect)
        self.disconnect = AsyncMock()


def _make_coordinator() -> HomewhizBluetoothUpdateCoordinator:
    """Build a coordinator without running DataUpdateCoordinator.__init__."""
    coord = object.__new__(HomewhizBluetoothUpdateCoordinator)
    coord.address = "00:11:22:33:44:55"
    coord._connection = None
    coord._connection_lock = asyncio.Lock()
    coord._available = False
    coord._grace_unsub = None
    coord._connected_at = None
    # Shadow the DataUpdateCoordinator methods so we don't need a real hass.
    coord.async_set_updated_data = Mock()
    coord.async_update_listeners = Mock()
    return coord


# --- MessageAccumulator ---


def test_accumulator_combines_two_part_message() -> None:
    acc = MessageAccumulator()
    assert acc.accumulate_message(bytearray([0, 0, 0, 0, 0, 0, 0, 1, 2, 3])) is None
    full = acc.accumulate_message(bytearray([0, 0, 0, 0, 1, 0, 0, 4, 5, 6]))
    assert full == bytearray([1, 2, 3, 4, 5, 6])


def test_accumulator_resets_on_unexpected_index() -> None:
    acc = MessageAccumulator()
    # index 1 without a preceding index 0 -> reset, returns None
    assert acc.accumulate_message(bytearray([0, 0, 0, 0, 1, 0, 0, 9])) is None
    # a fresh 0 then 1 still works afterwards
    assert acc.accumulate_message(bytearray([0, 0, 0, 0, 0, 0, 0, 7])) is None
    assert acc.accumulate_message(bytearray([0, 0, 0, 0, 1, 0, 0, 8])) == bytearray(
        [7, 8]
    )


# --- send_command (wait through reconnect + retry) ---


async def test_send_command_writes_payload_when_connected() -> None:
    coord = _make_coordinator()
    conn = _FakeConnection(connected=True)
    coord._connection = conn

    await coord.send_command(Command(index=0x1A, value=3))

    conn.write_gatt_char.assert_awaited_once_with(
        COMMAND_CHARACTERISTIC, bytearray([2, 4, 0, 4, 0, 0x1A, 1, 3])
    )


async def test_send_command_waits_for_in_flight_reconnect() -> None:
    coord = _make_coordinator()
    conn = _FakeConnection(connected=False)
    coord._connection = conn

    async def _reconnect() -> None:
        await asyncio.sleep(0.3)
        conn.is_connected = True

    flipper = asyncio.create_task(_reconnect())
    # Should wait for the reconnect rather than failing immediately.
    await coord.send_command(Command(index=1, value=1))
    await flipper

    conn.write_gatt_char.assert_awaited_once()


async def test_send_command_times_out_when_device_gone(monkeypatch) -> None:
    monkeypatch.setattr(bt, "_COMMAND_CONNECT_TIMEOUT", 0.4)
    coord = _make_coordinator()
    coord._connection = _FakeConnection(connected=False)

    with pytest.raises(HomeAssistantError):
        await coord.send_command(Command(index=1, value=1))


async def test_send_command_retries_after_transient_write_failure() -> None:
    coord = _make_coordinator()
    conn = _FakeConnection(connected=True, write_side_effect=[Exception("boom"), None])
    coord._connection = conn

    await coord.send_command(Command(index=1, value=1))

    assert conn.write_gatt_char.await_count == 2


async def test_send_command_raises_after_exhausting_attempts(monkeypatch) -> None:
    monkeypatch.setattr(bt, "_COMMAND_MAX_ATTEMPTS", 2)
    coord = _make_coordinator()
    conn = _FakeConnection(connected=True, write_side_effect=Exception("boom"))
    coord._connection = conn

    with pytest.raises(HomeAssistantError):
        await coord.send_command(Command(index=1, value=1))
    assert conn.write_gatt_char.await_count == 2


# --- availability debounce ---


def test_available_reflects_internal_flag() -> None:
    coord = _make_coordinator()
    coord._available = False
    assert coord.available is False
    coord._available = True
    assert coord.available is True


def test_grace_expiry_marks_unavailable_when_still_down() -> None:
    coord = _make_coordinator()
    coord._available = True
    coord._connection = None  # is_connected -> False

    coord._grace_expired(None)

    assert coord.available is False
    coord.async_set_updated_data.assert_called_once_with(None)


def test_grace_expiry_keeps_available_when_reconnected() -> None:
    coord = _make_coordinator()
    coord._available = True
    coord._connection = _FakeConnection(connected=True)

    coord._grace_expired(None)

    assert coord.available is True
    coord.async_set_updated_data.assert_not_called()
