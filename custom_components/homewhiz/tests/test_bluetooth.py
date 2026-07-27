"""Tests for the Bluetooth coordinator's disconnect handling.

The coordinator is built without DataUpdateCoordinator.__init__, and async code
runs through asyncio.run() from sync tests, so no extra plugin is needed.
Setting up that state requires touching private attributes.
"""

# ruff: noqa: SLF001

import asyncio
import contextlib
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from custom_components.homewhiz.bluetooth import HomewhizBluetoothUpdateCoordinator


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
    coord._connect_task = None
    coord._reconnect_interval_task = None
    hass = Mock()
    hass.create_task = scheduled.append
    hass.add_job = Mock()
    coord.hass = hass
    coord._hass = hass
    return coord


def test_stale_client_disconnect_is_ignored() -> None:
    scheduled: list = []
    coord = _make_coordinator(scheduled)
    superseded: Any = _FakeClient(connected=False)
    live: Any = _FakeClient()
    coord._connection = live

    asyncio.run(coord.handle_disconnect(superseded))
    for coro in scheduled:
        coro.close()

    assert coord._connection is live
    assert live.disconnect_calls == 0


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


def test_connect_on_dead_coordinator_is_refused() -> None:
    """After kill() a queued connect must not revive the coordinator."""
    coord = _make_coordinator([])
    coord.alive = False

    assert asyncio.run(coord.connect()) is False
    assert coord._connection is None


def test_kill_cancels_a_connect_in_progress() -> None:
    """Without cancellation, kill() would block on the lock the stuck connect holds."""
    coord = _make_coordinator([])

    async def run() -> tuple[float, bool]:
        async def stuck_connect() -> None:
            coord._connect_task = asyncio.current_task()
            try:
                async with coord._connection_lock:
                    await asyncio.sleep(100)  # simulates a hung establish_connection()
            finally:
                coord._connect_task = None

        task = asyncio.ensure_future(stuck_connect())
        await asyncio.sleep(0.01)  # let it acquire the lock first
        start = asyncio.get_running_loop().time()
        await coord.kill()
        elapsed = asyncio.get_running_loop().time() - start
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return elapsed, task.cancelled()

    elapsed, cancelled = asyncio.run(run())

    assert elapsed < 1
    assert cancelled


def test_kill_cancels_the_lock_holder_not_a_queued_connect() -> None:
    """A queued connect() must not steal kill()'s cancellation target."""
    coord = _make_coordinator([])

    async def hang_forever(**_kwargs: object) -> None:
        await asyncio.sleep(100)

    async def run() -> tuple[float, bool, bool]:
        with (
            patch(
                "homeassistant.components.bluetooth.async_ble_device_from_address",
                return_value=Mock(),
            ),
            patch(
                "custom_components.homewhiz.bluetooth.establish_connection",
                new_callable=AsyncMock,
                side_effect=hang_forever,
            ),
        ):
            first = asyncio.ensure_future(coord.connect())
            await asyncio.sleep(0.05)  # let it acquire the lock and hang inside
            second = asyncio.ensure_future(coord.connect())
            await asyncio.sleep(0.05)  # let it start waiting on the lock

            start = asyncio.get_running_loop().time()
            await asyncio.wait_for(coord.kill(), timeout=2)
            elapsed = asyncio.get_running_loop().time() - start

            for task in (first, second):
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            return elapsed, first.cancelled(), second.cancelled()

    elapsed, first_cancelled, second_cancelled = asyncio.run(run())

    assert elapsed < 1
    assert first_cancelled
    assert not second_cancelled  # it was never running anything to cancel


def test_kill_without_an_in_flight_connect_is_unaffected() -> None:
    coord = _make_coordinator([])

    asyncio.run(coord.kill())

    assert coord.alive is False
