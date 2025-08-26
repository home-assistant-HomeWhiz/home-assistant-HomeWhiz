import json
from pathlib import Path
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import generate_controls_from_config

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def config() -> ApplianceConfiguration:
    file_path = Path(__file__).parent / "fixtures" / "example_oven_config.json"
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x05\x00\x00\x00\xaa\x00\x14\x14\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x01\x00\x00(\x04\x00\x00\x00\x00"
        b"\x00\x06\x00\xe2\x00\x00\x00\x00\x01\x03\x02\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )

    controls = generate_controls_from_config("test_oven", config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "oven_booster": False,
            "oven_program": "program_static",
            "oven_skip_preheating": False,
            "oven_temperature": 200,
            "state": "device_state_off",
            "sub_state": None,
            "variable_delay": 98,
            "variable_oven_duration": 0,
            "variable_remaining": 6,
            "remote_control": True,
            "oven_warning_door_is_open": False,
            "oven_warning_door_locked": False,
            "oven_warning_error": False,
            "settings_brightness": 3,
            "settings_volume": "volume_high",
        },
    )
