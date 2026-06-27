import json
from pathlib import Path
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    EnumControl,
    WriteTimeControl,
    generate_controls_from_config,
)
from custom_components.homewhiz.homewhiz import Command

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def config() -> ApplianceConfiguration:
    file_path = (
        Path(__file__).parent / "fixtures" / "example_washing_machine_config.json"
    )
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_options_order(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_controls", config)
    controls_map = {control.key: control for control in controls}
    assert "washer_temperature" in controls_map
    temp_control = controls_map["washer_temperature"]
    assert isinstance(temp_control, EnumControl)
    test_case.assertListEqual(
        list(temp_control.options.values()),
        [
            "temperature_cold_wash",
            "temperature_20",
            "temperature_30",
            "temperature_40",
            "60c",
            "90c",
        ],
    )


def test_writable_start_delay(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_writable_start_delay", config)
    controls_map = {control.key: control for control in controls}

    # Writable counterpart of the read-only "delay_start#0" sensor.
    assert "delay_start_set#0" in controls_map
    delay = controls_map["delay_start_set#0"]
    assert isinstance(delay, WriteTimeControl)
    assert delay.minute_index is not None

    # 125 minutes -> 2h 5m, written to the hour and minute bytes.
    assert delay.set_value(125) == [
        Command(delay.hour_index, 2),
        Command(delay.minute_index, 5),
    ]

    # Negative values are clamped to zero.
    assert delay.set_value(-10) == [
        Command(delay.hour_index, 0),
        Command(delay.minute_index, 0),
    ]

    # Written commands round-trip through get_value.
    data = bytearray(max(delay.hour_index, delay.minute_index) + 1)
    for command in delay.set_value(125):
        data[command.index] = command.value
    assert delay.get_value(data) == 125
