import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase

import pytest
from dacite import from_dict
from homeassistant.components.climate import (  # type: ignore[import]
    PRESET_NONE,
    SWING_OFF,
    HVACMode,
)

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    ClimateControl,
    WriteNumericControl,
    forget_controls,
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
    file_path = Path(__file__).parent / "fixtures/example_ac_config.json"
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_test_off", config)
    values = {control.key: control.get_value(data_off) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "ac": {
                "air_conditioner_target_temperature": 26,
                "air_conditioner_room_temperature": 28,
                "air_conditioner_wind_strength": "wind_strength_low",
                "hvac": HVACMode.OFF,
                "preset": PRESET_NONE,
                "swing": SWING_OFF,
            },
        },
    )


def test_mode_auto(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_test_mode_auto", config)
    values = {control.key: control.get_value(data_auto) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "ac": {
                "air_conditioner_target_temperature": 23,
                "air_conditioner_room_temperature": 26,
                "air_conditioner_wind_strength": "wind_strength_auto",
                "hvac": HVACMode.AUTO,
                "preset": PRESET_NONE,
                "swing": SWING_OFF,
            },
        },
    )


def test_hvac_control(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("ac_test_hvac_control", config)
    controls_map = {control.key: control for control in controls}
    assert "ac" in controls_map
    ac_control = controls_map["ac"]
    assert isinstance(ac_control, ClimateControl)
    hvac_control = ac_control.hvac_mode

    # Get mode when off
    test_case.assertEqual(hvac_control.get_value(data_off), HVACMode.OFF)

    # Get mode when in auto state
    test_case.assertEqual(hvac_control.get_value(data_auto), HVACMode.AUTO)

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


@pytest.mark.parametrize("later_indices", [(77,), (77, 88)])
def test_duplicate_ac_target_keeps_existing_selection(
    config: ApplianceConfiguration, later_indices: tuple[int, ...]
) -> None:
    assert config.subPrograms is not None
    target = next(
        f
        for f in config.subPrograms
        if f.strKey == "AIR_CONDITIONER_TARGET_TEMPERATURE"
    )
    config = replace(
        config,
        settings=[
            replace(target, wifiArrayIndex=index, wfaWriteIndex=index + 1)
            for index in later_indices
        ],
    )
    key = f"ac-duplicate-target-{later_indices}"
    try:
        generated = generate_controls_from_config(key, config)
        assert [(type(c), c.key) for c in generated] == [
            (WriteNumericControl, "air_conditioner_target_temperature"),
            (ClimateControl, "ac"),
        ]
        standalone, climate = generated
        assert isinstance(standalone, WriteNumericControl)
        assert isinstance(climate, ClimateControl)
        # HA retains the first standalone entity, while AC extraction uses the
        # last configured target. Dedup must preserve both existing selections.
        assert standalone.read_index == target.wifiArrayIndex
        assert standalone.set_value(24) == Command(target.wifiArrayIndex, 24)
        assert climate.target_temperature.read_index == later_indices[-1]
        assert climate.target_temperature.set_value(24) == Command(
            later_indices[-1] + 1, 24
        )
    finally:
        forget_controls(key)
