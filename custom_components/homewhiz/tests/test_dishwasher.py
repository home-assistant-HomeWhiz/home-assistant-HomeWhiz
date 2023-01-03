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
            "STATE",
            "PROGRAM",
            "SUB_STATE",
            "DISHWASHER_TRAYWASH",
            "DISHWASHER_FAST+",
            "DISHWASHER_STEAMGLOSS",
            "DISHWASHER_EXTRARINSE",
            "DISHWASHER_HALFLOAD",
            "DISHWASHER_DELAY",
            "DISHWASHER_DURATION",
            "DISHWASHER_REMAINING",
            "REMOTE_CONTROL",
            "DISHWASHER_WARNING_NO_RINSE_AID",
            "DISHWASHER_WARNING_NO_SALT",
            "DISHWASHER_WARNING_NO_WATER",
            "DISHWASHER_WARNING_CHECK_THE_FILTER",
            "DISHWASHER_WARNING_DOOR_IS_OPEN",
            "DISHWASHER_WARNING_CALL_SERVICE",
            "DISHWASHER_LIQUID_DETERGENT_LOW",
            "SETTING_AUTO_DOOR",
            "SETTING_DETERGENT_TYPE",
            "DISHWASHER_RINSE_AID_LEVEL",
            "DISHWASHER_WATER_HARDNESS",
            "SETTING_INNER_ILLUMINATION",
        ],
    )
