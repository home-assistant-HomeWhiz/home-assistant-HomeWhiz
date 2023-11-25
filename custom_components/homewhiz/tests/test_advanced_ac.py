import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict
from homeassistant.components.climate import (  # type: ignore[import]
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    HVACMode,
)

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    generate_controls_from_config,
)
from custom_components.homewhiz.homewhiz import Command

test_case = TestCase()
test_case.maxDiff = None


data_swing_both = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x04<\x06\x00d\x05"
    b"\x1e\x00\x00\x14\n\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x07\x01\x00\x00\x00\x00"
)

data_swing_off = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x04<\x06\x00\x00\x00"
    b"\x1e\x00\x00\x14\n\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x07\x01\x00\x00\x00\x00"
)

data_swing_horizontal = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x04<\x06\x00\x00\x02"
    b"\x1e\x00\x00\x14\n\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x07\x01\x00\x00\x00\x00"
)


@pytest.fixture
def config() -> ApplianceConfiguration:
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "fixtures/example_ac_advanced_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_advanced_test", config)
    control_values = {
        control.key: control.get_value(data_swing_both) for control in controls
    }

    test_case.assertDictEqual(
        control_values,
        {
            "air_conditioner_soft_air": "air_conditioner_soft_air_off",
            "air_conditioner_instant_consumption": 0,
            "air_conditioner_sleep_mode_minute": 0,
            "air_conditioner_auto_switch_off": 0,
            "air_conditioner_auto_switch_on": 0,
            "air_conditioner_left_right_vane_control": "left_right_vane_control_5",
            "air_conditioner_up_down_vane_control": "up_down_vane_control_auto",
            "ac": {
                "air_conditioner_room_temperature": 15.0,
                "air_conditioner_target_temperature": 30.0,
                "air_conditioner_wind_strength": "6",
                "hvac": HVACMode.OFF,
                "swing": SWING_BOTH,
            },
        },
    )


def test_hvac_control(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_advanced_test_hvac_control", config)
    controls_map = {control.key: control for control in controls}
    assert "ac" in controls_map
    ac_control = controls_map["ac"]
    assert isinstance(ac_control, ClimateControl)
    hvac_control = ac_control.hvac_mode

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


def test_swing_control(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_advanced_test_swing_control", config)
    controls_map = {control.key: control for control in controls}
    assert "ac" in controls_map
    ac_control = controls_map["ac"]
    assert isinstance(ac_control, ClimateControl)
    swing_control = ac_control.swing

    test_case.assertTrue(swing_control.enabled)

    # Options
    test_case.assertListEqual(
        swing_control.options,
        [SWING_OFF, SWING_HORIZONTAL, SWING_VERTICAL, SWING_BOTH],
    )

    test_case.assertEquals(swing_control.get_value(data_swing_off), SWING_OFF)
    test_case.assertEquals(swing_control.get_value(data_swing_both), SWING_BOTH)
    test_case.assertEquals(
        swing_control.get_value(data_swing_horizontal), SWING_HORIZONTAL
    )

    # Turn on both axis
    test_case.assertListEqual(
        swing_control.set_value(SWING_BOTH, data_swing_off),
        [Command(index=39, value=100), Command(index=38, value=100)],
    )

    # Turn off both axis
    test_case.assertListEqual(
        swing_control.set_value(SWING_OFF, data_swing_both),
        [Command(index=39, value=0), Command(index=38, value=0)],
    )

    # Turn on single axis
    test_case.assertListEqual(
        swing_control.set_value(SWING_BOTH, data_swing_horizontal),
        [Command(index=38, value=100)],
    )

    # Turn off single axis
    test_case.assertListEqual(
        swing_control.set_value(SWING_OFF, data_swing_horizontal),
        [Command(index=39, value=0)],
    )

    # Swap axis
    test_case.assertListEqual(
        swing_control.set_value(SWING_VERTICAL, data_swing_horizontal),
        [Command(index=39, value=0), Command(index=38, value=100)],
    )
