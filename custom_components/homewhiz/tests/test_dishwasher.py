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
    file_path = os.path.join(dirname, "fixtures/example_dishwasher_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config(config)
    control_keys = [control.key for control in controls]

    test_case.assertListEqual(
        control_keys,
        [
            "state",
            "program",
            "sub_state",
            "dishwasher_traywash",
            "dishwasher_fastplus",
            "dishwasher_steamgloss",
            "dishwasher_extrarinse",
            "dishwasher_halfload",
            "dishwasher_delay",
            "dishwasher_duration",
            "dishwasher_remaining",
            "remote_control",
            "dishwasher_warning_no_rinse_aid",
            "dishwasher_warning_no_salt",
            "dishwasher_warning_no_water",
            "dishwasher_warning_check_the_filter",
            "dishwasher_warning_door_is_open",
            "dishwasher_warning_call_service",
            "dishwasher_liquid_detergent_low",
            "setting_auto_door",
            "setting_detergent_type",
            "dishwasher_rinse_aid_level",
            "dishwasher_water_hardness",
            "setting_inner_illumination",
        ],
    )
