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
    file_path = Path(__file__).parent / "fixtures" / "bauknecht-dryer.json"
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_dryer", config)
    control_keys = [control.key for control in controls]

    test_case.assertListEqual(
        control_keys,
        [
            "state",
            "dryer_program",
            "sub_state",
            "dryer_lowtemp_mode",
            "dryer_drying_level",
            "dryer_anti_creasing",
            "dryer_duration",
            "delay_start_set#0",
            "delay_start#0",
            "variable_duration",
            "variable_remaining",
            "variable_delay",
            "delay_start_time#0",
            "remote_control",
            "dryer_warning_door_is_open",
            "dryer_warning_tankfull",
            "dryer_warning_check_the_filter",
            "dryer_warning_check_the_condenser_filter",
            "dryer_warning_drum_empty",
            "dryer_message_child_lock",
            "dryer_message_end_program",
            "dryer_message_anti_creasing",
            "dryer_message_anti_creasing_finished",
            "setting_volume",
        ],
    )


def test_device_off(config: ApplianceConfiguration) -> None:
    """Remaining time is 0 and end time is unset when the dryer is off

    The dryer keeps reporting the selected programme's duration as
    remaining time while it is off, which made "Programme End Time"
    move forward with the clock (same issue as #336 for washers).
    """
    data = bytearray(100)
    data[49] = 20  # DEVICE_STATE_OFF
    data[40] = 2  # remaining hours
    data[41] = 25  # remaining minutes

    controls = generate_controls_from_config("test_dryer_off", config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertEqual(values["state"], "device_state_off")
    test_case.assertEqual(values["variable_remaining"], 0)
    test_case.assertIsNone(values["variable_delay"])


def test_device_running(config: ApplianceConfiguration) -> None:
    data = bytearray(100)
    data[49] = 30  # DEVICE_STATE_RUNNING
    data[40] = 2  # remaining hours
    data[41] = 25  # remaining minutes

    controls = generate_controls_from_config("test_dryer_running", config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertEqual(values["state"], "device_state_running")
    test_case.assertEqual(values["variable_remaining"], 145)
    test_case.assertIsNotNone(values["variable_delay"])
