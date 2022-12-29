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
    file_path = os.path.join(dirname, "fixtures/example_oven_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config):
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

    descriptions = generate_controls_from_config(config)
    values = {
        description.key: description.get_value(data) for description in descriptions
    }

    test_case.assertDictEqual(
        values,
        {
            "OVEN_BOOSTER": False,
            "OVEN_PROGRAM": "PROGRAM_STATIC",
            "OVEN_SKIP_PREHEATING": False,
            "OVEN_TEMPERATURE": 200,
            "STATE": "DEVICE_STATE_OFF",
            "SUB_STATE": None,
            "VARIABLE_DELAY": 98,
            "VARIABLE_OVEN_DURATION": 0,
            "VARIABLE_REMAINING": 6,
        },
    )
