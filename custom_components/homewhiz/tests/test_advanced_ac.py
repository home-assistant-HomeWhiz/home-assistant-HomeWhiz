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
def config():
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "fixtures/example_ac_advanced_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test(config):
    controls = generate_controls_from_config(config)
    control_keys = [control.key for control in controls]

    test_case.assertListEqual(
        control_keys,
        [
            "AIR_CONDITIONER_SOFT_AIR",
            "AIR_CONDITIONER_UP_DOWN_VANE_CONTROL",
            "AIR_CONDITIONER_LEFT_RIGHT_VANE_CONTROL",
            "AIR_CONDITIONER_INSTANT_CONSUMPTION",
            "AIR_CONDITIONER_SLEEP_MODE_MINUTE",
            "AIR_CONDITIONER_AUTO_SWITCH_OFF",
            "AIR_CONDITIONER_AUTO_SWITCH_ON",
            "AC",
        ],
    )
