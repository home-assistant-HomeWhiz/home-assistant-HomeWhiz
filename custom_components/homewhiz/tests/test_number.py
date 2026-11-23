"""Tests for the writable start delay number."""

import asyncio
from unittest.mock import AsyncMock, Mock

from custom_components.homewhiz.appliance_controls import WriteTimeControl
from custom_components.homewhiz.homewhiz import Command, HomewhizCoordinator
from custom_components.homewhiz.number import HomeWhizNumberEntity


def test_number_sends_hour_and_minute_as_one_write() -> None:
    entity = object.__new__(HomeWhizNumberEntity)
    entity._control = WriteTimeControl("delay_start_set#0", 48, 49)
    coordinator = Mock()
    coordinator.send_commands = AsyncMock()
    coordinator.send_command = AsyncMock()
    entity.coordinator = coordinator

    asyncio.run(entity.async_set_native_value(120))

    coordinator.send_commands.assert_awaited_once_with([Command(48, 2), Command(49, 0)])
    coordinator.send_command.assert_not_awaited()


def test_default_send_commands_sends_in_order_without_a_pause() -> None:
    sent: list[Command] = []

    class _Coordinator(HomewhizCoordinator):
        async def connect(self) -> bool:
            return True

        @property
        def is_connected(self) -> bool:
            return True

        async def send_command(self, command: Command) -> None:
            sent.append(command)

    coordinator = object.__new__(_Coordinator)

    asyncio.run(coordinator.send_commands([Command(42, 2), Command(43, 0)]))

    assert sent == [Command(42, 2), Command(43, 0)]
