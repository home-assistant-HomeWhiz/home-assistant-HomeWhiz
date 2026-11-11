"""Tests with the configuration of a real Arcelik air conditioner (model 9200351100).

The fixture is the configuration from the diagnostics of the reporter of issue
#509. Hass-free like the other platform tests: the coordinator is a mock, the
packets are built by hand with the read indices of this appliance (power 43,
program 34, target temperature 35).
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from dacite import from_dict
from homeassistant.components.climate import HVACMode

from custom_components.homewhiz.api import ApplianceContents
from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    forget_controls,
    generate_controls_from_config,
)
from custom_components.homewhiz.climate import HomeWhizClimateEntity
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.homewhiz import Command

POWER_READ_INDEX = 43
POWER_WRITE_INDEX = 44
PROGRAM_INDEX = 34
TARGET_TEMPERATURE_INDEX = 35
POWER_ON = 10
POWER_OFF = 20
PROGRAM_HEATING = 4
PROGRAM_AUTO = 6
# Raw value 60 with the factor 0.5 of the config is 30 degrees.
TARGET_TEMPERATURE_30 = 60


@pytest.fixture
def config() -> ApplianceConfiguration:
    file_path = Path(__file__).parent / "fixtures" / "arcelik-ac.json"
    with file_path.open(encoding="utf-8") as file:
        return from_dict(ApplianceConfiguration, json.load(file))


def _packet(power: int, program: int = PROGRAM_HEATING) -> bytearray:
    packet = bytearray(120)
    packet[POWER_READ_INDEX] = power
    packet[PROGRAM_INDEX] = program
    packet[TARGET_TEMPERATURE_INDEX] = TARGET_TEMPERATURE_30
    return packet


def _climate_control(config: ApplianceConfiguration) -> ClimateControl:
    forget_controls("real_ac")
    controls = generate_controls_from_config("real_ac", config)
    return next(c for c in controls if isinstance(c, ClimateControl))


def _entity(
    config: ApplianceConfiguration, packet: bytearray
) -> tuple[HomeWhizClimateEntity, Mock]:
    coordinator = Mock()
    coordinator.data = packet
    coordinator.send_command = AsyncMock()
    entry_data = EntryData(
        ids=Mock(),
        contents=ApplianceContents(config=Mock(), localization={}),
        appliance_info=None,
        cloud_config=None,
    )
    entity = HomeWhizClimateEntity(
        coordinator=coordinator,
        control=_climate_control(config),
        device_name="Test AC",
        data=entry_data,
    )
    return entity, coordinator


def _sent(coordinator: Mock) -> list[Command]:
    return [call.args[0] for call in coordinator.send_command.await_args_list]


def test_the_config_builds_one_climate_control(config: ApplianceConfiguration) -> None:
    forget_controls("real_ac")
    controls = generate_controls_from_config("real_ac", config)

    assert [control.key for control in controls] == [
        "air_conditioner_soft_air",
        "air_conditioner_up_down_vane_control",
        "air_conditioner_left_right_vane_control",
        "air_conditioner_instant_consumption",
        "air_conditioner_sleep_mode_minute",
        "air_conditioner_auto_switch_off",
        "air_conditioner_auto_switch_on",
        "ac",
    ]
    hvac = _climate_control(config).hvac_mode
    assert hvac.options == [
        HVACMode.COOL,
        HVACMode.AUTO,
        HVACMode.DRY,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.OFF,
    ]
    assert hvac.state.read_index == POWER_READ_INDEX
    assert hvac.state.write_index == POWER_WRITE_INDEX
    assert hvac.program.read_index == PROGRAM_INDEX


def test_the_off_packet_still_holds_the_last_mode(
    config: ApplianceConfiguration,
) -> None:
    hvac = _climate_control(config).hvac_mode

    assert hvac.get_value(_packet(POWER_OFF)) == HVACMode.OFF
    assert hvac.remembered_mode(_packet(POWER_OFF)) == HVACMode.HEAT
    assert hvac.get_value(_packet(POWER_ON)) == HVACMode.HEAT


def test_turn_on_comes_back_in_the_remembered_mode(
    config: ApplianceConfiguration,
) -> None:
    """Issue #509: the power-on command used to be followed by a switch to auto."""
    entity, coordinator = _entity(config, _packet(POWER_OFF))

    asyncio.run(entity.async_turn_on())

    assert _sent(coordinator) == [Command(POWER_WRITE_INDEX, POWER_ON)]


def test_the_old_fallback_switched_the_program_to_auto(
    config: ApplianceConfiguration,
) -> None:
    """What turn_on sent before the fix, for an AC that remembers heat."""
    hvac = _climate_control(config).hvac_mode

    assert hvac.set_value(HVACMode.AUTO, _packet(POWER_OFF)) == [
        Command(POWER_WRITE_INDEX, POWER_ON),
        Command(PROGRAM_INDEX, PROGRAM_AUTO),
    ]


def test_turn_on_of_a_running_ac_changes_nothing(
    config: ApplianceConfiguration,
) -> None:
    entity, coordinator = _entity(config, _packet(POWER_ON))

    asyncio.run(entity.async_turn_on())

    assert _sent(coordinator) == []


def test_turn_off_of_an_ac_that_is_off_does_not_break_turn_on(
    config: ApplianceConfiguration,
) -> None:
    entity, coordinator = _entity(config, _packet(POWER_OFF))

    asyncio.run(entity.async_turn_off())
    coordinator.send_command.reset_mock()
    asyncio.run(entity.async_turn_on())

    assert _sent(coordinator) == [Command(POWER_WRITE_INDEX, POWER_ON)]


def test_turn_off_sends_the_power_off_command(
    config: ApplianceConfiguration,
) -> None:
    entity, coordinator = _entity(config, _packet(POWER_ON))

    asyncio.run(entity.async_turn_off())

    assert _sent(coordinator) == [Command(POWER_WRITE_INDEX, POWER_OFF)]
