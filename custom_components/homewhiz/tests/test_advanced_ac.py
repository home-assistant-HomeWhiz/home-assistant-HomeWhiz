import json
from pathlib import Path
from unittest import TestCase

import pytest
from dacite import from_dict
from homeassistant.components.climate import (  # type: ignore[import]
    PRESET_BOOST,
    PRESET_NONE,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    HVACMode,
)

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    NumericControl,
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

data_jet_mode_on = bytearray(
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x04<\x06\x01d\x05"
    b"\x1e\x00\x00\x14\n\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x07\x01\x00\x00\x00\x00"
)


@pytest.fixture
def config() -> ApplianceConfiguration:
    file_path = Path(__file__).parent / "fixtures/example_ac_advanced_config.json"
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


@pytest.fixture
def config_with_correct_consumption_factor() -> ApplianceConfiguration:
    """Same fixture as `config`, except AIR_CONDITIONER_INSTANT_CONSUMPTION
    already reports the correct factor (0.1) instead of the known-bad 1.
    Used to prove the correction in extract_ac_control is a no-op once
    Arcelik's own data is already correct."""
    file_path = (
        Path(__file__).parent
        / "fixtures/example_ac_advanced_config_correct_factor.json"
    )
    with file_path.open() as file:
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
                "preset": PRESET_NONE,
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

    test_case.assertEqual(swing_control.get_value(data_swing_off), SWING_OFF)
    test_case.assertEqual(swing_control.get_value(data_swing_both), SWING_BOTH)
    test_case.assertEqual(
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


def test_preset_control(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_advanced_test_preset_control", config)
    controls_map = {control.key: control for control in controls}
    assert "ac" in controls_map
    ac_control = controls_map["ac"]
    assert isinstance(ac_control, ClimateControl)
    preset_control = ac_control.preset_mode

    test_case.assertTrue(preset_control.enabled)

    # Options
    test_case.assertListEqual(
        preset_control.options,
        [PRESET_NONE, PRESET_BOOST],
    )

    test_case.assertEqual(preset_control.get_value(data_swing_both), PRESET_NONE)
    test_case.assertEqual(preset_control.get_value(data_jet_mode_on), PRESET_BOOST)

    # Turn on
    test_case.assertListEqual(
        preset_control.set_value(PRESET_BOOST),
        [Command(index=37, value=1)],
    )

    # Turn off
    test_case.assertListEqual(
        preset_control.set_value(PRESET_NONE),
        [Command(index=37, value=0)],
    )


def test_instant_consumption_factor_is_corrected(
    config: ApplianceConfiguration,
) -> None:
    """Arcelik's CONFIGURATION reports factor=1 for
    AIR_CONDITIONER_INSTANT_CONSUMPTION, but the real-world value
    (confirmed against the appliance's own user manual and its on-device
    remote display) is raw_byte * 0.1 kW. extract_ac_control corrects
    this for AC appliances only."""
    controls = generate_controls_from_config(
        "ac_advanced_test_instant_consumption_bad_factor", config
    )
    controls_map = {control.key: control for control in controls}
    consumption_control = controls_map["air_conditioner_instant_consumption"]
    assert isinstance(consumption_control, NumericControl)

    test_case.assertEqual(consumption_control.bounds.factor, 0.1)

    data = bytearray(data_swing_both)
    data[45] = 4
    consumption_value = consumption_control.get_value(data)
    assert consumption_value is not None
    test_case.assertAlmostEqual(consumption_value, 0.4)


def test_instant_consumption_factor_correction_is_idempotent(
    config_with_correct_consumption_factor: ApplianceConfiguration,
) -> None:
    """If Arcelik ever reports the already-correct factor (0.1), the
    correction must not touch it further (e.g. must not divide it again)."""
    controls = generate_controls_from_config(
        "ac_advanced_test_instant_consumption_correct_factor",
        config_with_correct_consumption_factor,
    )
    controls_map = {control.key: control for control in controls}
    consumption_control = controls_map["air_conditioner_instant_consumption"]
    assert isinstance(consumption_control, NumericControl)

    test_case.assertEqual(consumption_control.bounds.factor, 0.1)

    data = bytearray(data_swing_both)
    data[45] = 4
    consumption_value = consumption_control.get_value(data)
    assert consumption_value is not None
    test_case.assertAlmostEqual(consumption_value, 0.4)


def test_unrelated_numeric_controls_are_not_touched(
    config: ApplianceConfiguration,
) -> None:
    """The instant-consumption factor correction must be scoped to that one
    feature only - other NumericControl features (e.g. sleep mode minutes)
    must keep whatever factor/unit Arcelik's CONFIGURATION reports."""
    controls = generate_controls_from_config(
        "ac_advanced_test_unrelated_numeric_controls", config
    )
    controls_map = {control.key: control for control in controls}
    sleep_mode_minute = controls_map["air_conditioner_sleep_mode_minute"]
    assert isinstance(sleep_mode_minute, NumericControl)

    test_case.assertEqual(sleep_mode_minute.bounds.factor, 1)
    test_case.assertEqual(sleep_mode_minute.bounds.unit, "")
