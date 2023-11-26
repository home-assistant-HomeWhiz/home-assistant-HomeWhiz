import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import generate_controls_from_config

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def config() -> ApplianceConfiguration:
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(
        dirname, "fixtures/example_washing_machine_with_dryer_config.json"
    )
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00\xb8d\x13\xab\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x14\x80(\x0e\x00\x00\x00\x00\x00\x02\x14\x00"
        b"\x00\x80\x80\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x01\x00\x00\x00\x00\x13\x00\x00\x00\x00\x00\x00"
    )
    controls = generate_controls_from_config("test_washing_machine_with_dryer", config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_off",
            "sub_state": "washer_substate_program_started",
            "washer_dry": "dry_off",
            "washer_extrarinse": False,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": True,
            "washer_prewash": False,
            "washer_program": None,
            "washer_spin": "spin_1400",
            "washer_temperature": "temperature_40",
            "washer_steam": False,
            "washer_duration": 140,
            "washer_remaining": 0,
            "washer_delay": None,
            "remote_control": False,
            "washer_warning_door_is_open": False,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_low",
            "washer_soaking": False,
            "washer_night": False,
            "washer_rinse_count": 0,
            "washer_anticrease": False,
            "washer_add_water": False,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 0,
            "delay_start_time#0": None,
        },
    )
