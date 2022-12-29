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
    file_path = os.path.join(dirname, "fixtures/example_washing_machine_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_on(config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000000a011e0c"
        "0000000080021102110000000000000000000000000000000100000000000001070000000000"
    )
    descriptions = generate_controls_from_config(config)
    values = {
        description.key: description.get_value(data) for description in descriptions
    }

    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "SUB_STATE": None,
            "WASHER_EXTRARINSE": False,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": False,
            "WASHER_PHR": False,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1200 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 137,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 137,
        },
    )


def test_running(config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c"
        "0080000080021100398080010000000000000000000080808100800000008001078000808000"
    )
    descriptions = generate_controls_from_config(config)
    values = {
        description.key: description.get_value(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_RUNNING",
            "SUB_STATE": "WASHER_SUBSTATE_WASHING",
            "WASHER_EXTRARINSE": False,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": False,
            "WASHER_PHR": False,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1200 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 137,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 57,
        },
    )


def test_spinning(config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c"
        "00808080800211000a8080020000000000000000008080808180800000008081078000808000"
    )
    descriptions = generate_controls_from_config(config)
    values = {
        description.key: description.get_value(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_RUNNING",
            "SUB_STATE": "WASHER_SUBSTATE_SPIN",
            "WASHER_EXTRARINSE": False,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": False,
            "WASHER_PHR": False,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1200 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 137,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 10,
        },
    )


def test_delay_defined(config):
    data = bytearray.fromhex(
        "003853e0ab0100000000000000000000000000000000000000000300000000000000000a01280e"
        "000000008002100210012c000000000000000000010000000100000000000001078000000000"
    )
    descriptions = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in descriptions}
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "SUB_STATE": None,
            "WASHER_EXTRARINSE": False,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": False,
            "WASHER_PHR": False,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1400 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_STEAM": False,
            "WASHER_REMAINING": 136,
            "WASHER_DELAY": 104,
            "WASHER_DURATION": 136,
        },
    )
