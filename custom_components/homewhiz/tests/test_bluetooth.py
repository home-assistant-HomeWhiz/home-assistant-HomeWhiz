"""Tests for the Bluetooth coordinator's disconnect handling.

The coordinator is built without DataUpdateCoordinator.__init__, and async code
runs through asyncio.run() from sync tests, so no extra plugin is needed.
Setting up that state requires touching private attributes.
"""

# ruff: noqa: SLF001

import asyncio
from typing import Any
from unittest.mock import Mock

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
    hass = Mock()
    hass.create_task = scheduled.append
    hass.add_job = Mock()
    coord.hass = hass
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
