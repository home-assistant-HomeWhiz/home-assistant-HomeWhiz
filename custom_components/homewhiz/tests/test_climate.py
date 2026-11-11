"""Tests for HomeWhizClimateEntity.

Deliberately hass-free (project convention, see test_config_flow.py): the
async lifecycle methods here are exercised with Mock()-based coordinators
rather than a real hass instance.
"""

# ruff: noqa: SLF001

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from dacite import from_dict
from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature

from custom_components.homewhiz.api import ApplianceContents
from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    generate_controls_from_config,
)
from custom_components.homewhiz.climate import HomeWhizClimateEntity
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.homewhiz import Command

data_off = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x04\x1a\x00\x00\x00\x00\x1c\x00\x00\x14\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)
# The same packet with the power byte (index 43) switched on: running in heat mode.
data_heating = bytearray(data_off)
data_heating[43] = 10


def _entry_data() -> EntryData:
    return EntryData(
        ids=Mock(),
        contents=ApplianceContents(config=Mock(), localization={}),
        appliance_info=None,
        cloud_config=None,
    )


@pytest.fixture
def climate_entity() -> HomeWhizClimateEntity:
    file_path = Path(__file__).parent / "fixtures/example_ac_config.json"
    with file_path.open() as file:
        config = from_dict(ApplianceConfiguration, json.load(file))
    controls = generate_controls_from_config("ac_test_turn_on", config)
    control = next(c for c in controls if isinstance(c, ClimateControl))

    coordinator = Mock()
    coordinator.data = data_off
    coordinator.send_command = AsyncMock()

    return HomeWhizClimateEntity(
        coordinator=coordinator,
        control=control,
        device_name="Test AC",
        data=_entry_data(),
    )


def _sent(climate_entity: HomeWhizClimateEntity) -> list[Command]:
    send_command = climate_entity.coordinator.send_command  # type: ignore[attr-defined]
    return [call.args[0] for call in send_command.await_args_list]  # type: ignore[attr-defined]


def test_turn_on_restores_the_mode_the_appliance_remembers(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    """Issue #509: after a restart of Home Assistant nothing was recorded, the
    fallback switched the program to auto right after the power-on command.
    The appliance still reports the mode it was in (here heat), so only the
    power-on command may be sent."""
    control = climate_entity._control.hvac_mode
    assert control.remembered_mode(data_off) == HVACMode.HEAT
    assert climate_entity.hvac_mode == HVACMode.OFF

    asyncio.run(climate_entity.async_turn_on())

    assert _sent(climate_entity) == [Command(43, 10)]


def test_turn_on_falls_back_when_the_appliance_reports_no_mode(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    """Regression test for #447: the fallback must be a mode this appliance
    knows. It used to be HVACMode.HEAT_COOL, which no AC control maps to, so
    HvacControl.set_value() raised ValueError."""
    data = bytearray(data_off)
    data[34] = 0x7F  # program byte that is not one of the options
    climate_entity.coordinator.data = data  # type: ignore[assignment]
    assert climate_entity._control.hvac_mode.remembered_mode(data) is None

    asyncio.run(climate_entity.async_turn_on())

    assert _sent(climate_entity) == [Command(43, 10), Command(34, 6)]


def test_turn_off_of_an_appliance_that_is_off_does_not_break_turn_on(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    """Issue #509, second finding: turn_off on an appliance that was already
    off remembered HVACMode.OFF, the next turn_on then sent the power-off
    command again."""
    asyncio.run(climate_entity.async_turn_off())
    climate_entity.coordinator.send_command.reset_mock()  # type: ignore[attr-defined]

    asyncio.run(climate_entity.async_turn_on())

    assert _sent(climate_entity) == [Command(43, 10)]


def test_turn_on_of_a_running_appliance_sends_nothing(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    climate_entity.coordinator.data = data_heating  # type: ignore[assignment]
    assert climate_entity.hvac_mode == HVACMode.HEAT

    asyncio.run(climate_entity.async_turn_on())

    assert _sent(climate_entity) == []


def test_turn_off_sends_the_power_off_command(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    climate_entity.coordinator.data = data_heating  # type: ignore[assignment]

    asyncio.run(climate_entity.async_turn_off())

    assert _sent(climate_entity) == [Command(43, 20)]


def test_temperature_values_through_home_assistants_public_names(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    """HA reads these public names on every version: directly before 2026.11, via
    its deprecation shim to the native_* properties from 2026.11 on. The entity
    must answer the same way on both."""
    control = climate_entity._control
    data = climate_entity.coordinator.data
    assert data is not None

    assert climate_entity.temperature_unit == UnitOfTemperature.CELSIUS
    assert climate_entity.current_temperature == control.current_temperature.get_value(
        data
    )
    assert climate_entity.target_temperature == control.target_temperature.get_value(
        data
    )
    assert (
        climate_entity.target_temperature_low
        == control.target_temperature.bounds.lowerLimit
    )
    assert (
        climate_entity.target_temperature_high
        == control.target_temperature.bounds.upperLimit
    )
