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
from homeassistant.const import UnitOfTemperature

from custom_components.homewhiz.api import ApplianceContents
from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    generate_controls_from_config,
)
from custom_components.homewhiz.climate import HomeWhizClimateEntity
from custom_components.homewhiz.config_flow import EntryData

data_off = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x04\x1a\x00\x00\x00\x00\x1c\x00\x00\x14\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


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


def test_turn_on_without_previous_mode_uses_a_supported_mode(
    climate_entity: HomeWhizClimateEntity,
) -> None:
    """Regression test: async_turn_on() used to fall back to HVACMode.HEAT_COOL
    when no previous mode was recorded (e.g. after every HA restart, since
    _previous_hvac_mode is never persisted/restored). No AC control maps to
    HEAT_COOL (see program_suffix_to_hvac_mode), so HvacControl.set_value()
    raised ValueError("Unrecognized fan mode heat_cool") on the very first
    turn_on of a session."""
    assert climate_entity._previous_hvac_mode is None

    asyncio.run(climate_entity.async_turn_on())

    assert climate_entity.coordinator.send_command.await_count > 0  # type: ignore[attr-defined]


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
