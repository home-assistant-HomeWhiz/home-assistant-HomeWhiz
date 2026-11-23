"""Tests for the Bluetooth coordinator's disconnect handling.

The coordinator is built without DataUpdateCoordinator.__init__, and async code
runs through asyncio.run() from sync tests, so no extra plugin is needed.
Setting up that state requires touching private attributes.
"""

# ruff: noqa: SLF001

import asyncio
from typing import Any
from unittest.mock import Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.homewhiz.bluetooth import (
    BT_COMMAND_GAP,
    HomewhizBluetoothUpdateCoordinator,
)
from custom_components.homewhiz.homewhiz import Command


class _FakeClient:
    def __init__(self, connected: bool = True) -> None:
        self.disconnect_calls = 0
        self._connected = connected

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._connected = False


def _make_coordinator(scheduled: list) -> HomewhizBluetoothUpdateCoordinator:
    coord = object.__new__(HomewhizBluetoothUpdateCoordinator)
    coord.address = "00:11:22:33:44:55"
    coord.alive = True
    coord._connection = None
    coord._connection_lock = asyncio.Lock()
    coord._device = None
    coord._device_lock = asyncio.Lock()
    hass = Mock()
    hass.create_task = scheduled.append
    hass.async_create_background_task = lambda coro, name: scheduled.append(coro)
    hass.add_job = Mock()
    coord.hass = hass
    return coord


def test_reconnect_does_not_block_startup_and_recovers(tmp_path: Any) -> None:
    """A connectable proxy advertisement can arrive after startup has drained."""

    async def run() -> None:
        hass = HomeAssistant(str(tmp_path))
        coord = _make_coordinator([])
        coord.hass = hass
        coord.reconnecting_lock = asyncio.Lock()
        old_client: Any = _FakeClient(connected=False)
        coord._connection = old_client
        waiting = asyncio.Event()
        advertised = asyncio.Event()
        connected = asyncio.Event()

        async def retry_wait(delay: float) -> None:
            assert delay == 60
            waiting.set()
            await advertised.wait()

        async def connect() -> None:
            new_client: Any = _FakeClient()
            coord._connection = new_client
            connected.set()

        with (
            patch.object(coord, "connect", side_effect=connect),
            patch(
                "custom_components.homewhiz.bluetooth.bluetooth.async_address_present",
                side_effect=lambda *_args, **_kwargs: advertised.is_set(),
            ) as present,
            patch("custom_components.homewhiz.bluetooth.asyncio") as bt_asyncio,
        ):
            # Sleep must be awaitable, as it is in the real loop.
            bt_asyncio.sleep = retry_wait
            with patch.object(coord, "async_set_updated_data"):
                await coord.handle_disconnect(old_client)
                await asyncio.wait_for(waiting.wait(), timeout=2)
                startup = asyncio.create_task(hass.async_block_till_done())
                try:
                    done, _ = await asyncio.wait({startup}, timeout=0.2)
                    assert startup in done, "Reconnect blocked HA startup task drain"
                    assert not coord.is_connected
                finally:
                    advertised.set()
                    await asyncio.wait_for(connected.wait(), timeout=2)
                    await startup
                assert coord.is_connected
                present.assert_called_with(hass, coord.address, connectable=True)

    asyncio.run(run())


def test_stale_client_disconnect_is_ignored() -> None:
    scheduled: list = []
    coord = _make_coordinator(scheduled)
    superseded: Any = _FakeClient(connected=False)
    live: Any = _FakeClient()
    coord._connection = live

    asyncio.run(coord.handle_disconnect(superseded))
    for coro in scheduled:
        coro.close()

    assert live.disconnect_calls == 0
    assert coord._connection is live


def test_live_client_disconnect_tears_down() -> None:
    scheduled: list = []
    coord = _make_coordinator(scheduled)
    live: Any = _FakeClient()
    coord._connection = live

    asyncio.run(coord.handle_disconnect(live))
    for coro in scheduled:
        coro.close()

    assert coord._connection is None
    assert live.disconnect_calls == 1


def test_disconnect_without_client_tears_down() -> None:
    """Callers that pass no client (e.g. interval reconnect) keep working."""
    scheduled: list = []
    coord = _make_coordinator(scheduled)
    live: Any = _FakeClient()
    coord._connection = live

    asyncio.run(coord.handle_disconnect())
    for coro in scheduled:
        coro.close()

    assert coord._connection is None
    assert live.disconnect_calls == 1


class _WritingClient:
    """Records the GATT writes and can drop the link after a number of writes."""

    def __init__(self, writes: list[tuple[int, int]], drop_after: int | None = None):
        self._writes = writes
        self._drop_after = drop_after

    @property
    def is_connected(self) -> bool:
        return self._drop_after is None or len(self._writes) < self._drop_after

    async def write_gatt_char(self, uuid: str, payload: bytearray) -> None:
        self._writes.append((payload[5], payload[7]))


def _coordinator_with_client(client: Any) -> HomewhizBluetoothUpdateCoordinator:
    coord = _make_coordinator([])
    coord._connection = client
    return coord


def test_multi_command_write_waits_between_commands() -> None:
    writes: list[tuple[int, int]] = []
    sleeps: list[float] = []
    coord = _coordinator_with_client(_WritingClient(writes))

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    with patch("custom_components.homewhiz.bluetooth.asyncio.sleep", fake_sleep):
        asyncio.run(coord.send_commands([Command(48, 2), Command(49, 0)]))

    assert writes == [(48, 2), (49, 0)]
    assert sleeps == [BT_COMMAND_GAP]


def test_single_command_write_does_not_wait() -> None:
    writes: list[tuple[int, int]] = []
    sleeps: list[float] = []
    coord = _coordinator_with_client(_WritingClient(writes))

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    with patch("custom_components.homewhiz.bluetooth.asyncio.sleep", fake_sleep):
        asyncio.run(coord.send_commands([Command(34, 10)]))

    assert writes == [(34, 10)]
    assert sleeps == []


def test_other_command_cannot_slip_into_a_multi_command_write() -> None:
    writes: list[tuple[int, int]] = []
    coord = _coordinator_with_client(_WritingClient(writes))
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds: float) -> None:
        # Stay in the pause long enough for the other task to try its write.
        for _ in range(5):
            await real_sleep(0)

    async def scenario() -> None:
        sequence = asyncio.create_task(
            coord.send_commands([Command(48, 2), Command(49, 0)])
        )
        await real_sleep(0)
        other = asyncio.create_task(coord.send_command(Command(34, 30)))
        await asyncio.gather(sequence, other)

    with patch("custom_components.homewhiz.bluetooth.asyncio.sleep", fake_sleep):
        asyncio.run(scenario())

    assert writes == [(48, 2), (49, 0), (34, 30)]


def test_link_lost_between_commands_is_reported() -> None:
    writes: list[tuple[int, int]] = []
    coord = _coordinator_with_client(_WritingClient(writes, drop_after=1))

    async def fake_sleep(seconds: float) -> None:
        return None

    with (
        patch("custom_components.homewhiz.bluetooth.asyncio.sleep", fake_sleep),
        pytest.raises(HomeAssistantError, match="Only 1 of 2 commands"),
    ):
        asyncio.run(coord.send_commands([Command(48, 2), Command(49, 0)]))

    assert writes == [(48, 2)]


def test_not_connected_before_first_command_keeps_the_original_error() -> None:
    coord = _coordinator_with_client(None)

    with pytest.raises(HomeAssistantError, match="Device not connected"):
        asyncio.run(coord.send_commands([Command(48, 2), Command(49, 0)]))
