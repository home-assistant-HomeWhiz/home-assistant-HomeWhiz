import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict
from homeassistant.components.climate import SWING_OFF, HVACMode  # type: ignore[import]

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    generate_controls_from_config,
)
from custom_components.homewhiz.homewhiz import Command

test_case = TestCase()
test_case.maxDiff = None


data_off = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x04\x1a\x00\x00\x00\x00\x1c\x00\x00\x14\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)

data_auto = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x06\x17\x03\x00\x00\x00\x1a\x00\x00\n\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


@pytest.fixture
def config() -> ApplianceConfiguration:
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "fixtures/example_ac_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data_off) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "AC": {
                "AIR_CONDITIONER_TARGET_TEMPERATURE": 26,
                "AIR_CONDITIONER_ROOM_TEMPERATURE": 28,
                "AIR_CONDITIONER_WIND_STRENGTH": "WIND_STRENGTH_LOW",
                "HVAC": HVACMode.OFF,
                "SWING": SWING_OFF,
            },
        },
    )


def test_mode_auto(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data_auto) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "AC": {
                "AIR_CONDITIONER_TARGET_TEMPERATURE": 23,
                "AIR_CONDITIONER_ROOM_TEMPERATURE": 26,
                "AIR_CONDITIONER_WIND_STRENGTH": "WIND_STRENGTH_AUTO",
                "HVAC": HVACMode.AUTO,
                "SWING": SWING_OFF,
            },
        },
    )


def test_hvac_control(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config(config)
    controls_map = {control.key: control for control in controls}
    assert "AC" in controls_map
    ac_control = controls_map["AC"]
    assert isinstance(ac_control, ClimateControl)
    hvac_control = ac_control.hvac_mode

    # Get mode when off
    test_case.assertEquals(hvac_control.get_value(data_off), HVACMode.OFF)

    # Get mode when in auto state
    test_case.assertEquals(hvac_control.get_value(data_auto), HVACMode.AUTO)

    # Turn on with the same mode
    test_case.assertListEqual(
        hvac_control.set_value(HVACMode.HEAT, data_off), [Command(43, 10)]
    )

    # Turn on with the different mode
    test_case.assertListEqual(
        hvac_control.set_value(HVACMode.AUTO, data_off),
        [Command(43, 10), Command(34, 6)],
    )

    # Turn off
    test_case.assertListEqual(
        hvac_control.set_value(HVACMode.OFF, data_auto),
        [Command(43, 20)],
    )

    # Options
    test_case.assertListEqual(
        hvac_control.options,
        [
            HVACMode.COOL,
            HVACMode.AUTO,
            HVACMode.DRY,
            HVACMode.HEAT,
            HVACMode.FAN_ONLY,
            HVACMode.OFF,
        ],
    )
