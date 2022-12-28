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
    file_path = os.path.join(
        dirname, "fixtures/example_washing_machine_with_dryer_config.json"
    )
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config):
    data = bytearray(
        b"\x00\xb8d\x13\xab\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x14\x80(\x0e\x00\x00\x00\x00\x00\x02\x14\x00"
        b"\x00\x80\x80\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x01\x00\x00\x00\x00\x13\x00\x00\x00\x00\x00\x00"
    )
    descriptions = generate_controls_from_config(config)
    values = {
        description.key: description.get_value(data) for description in descriptions
    }

    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_OFF",
            "SUB_STATE": "WASHER_SUBSTATE_PROGRAM_STARTED",
            "WASHER_DRY": "DRY_OFF",
            "WASHER_EXTRARINSE": False,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": True,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": None,
            "WASHER_SPIN": "SPIN_1400",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 140,
            "WASHER_REMAINING": 0,
            "WASHER_DELAY": 0,
        },
    )
