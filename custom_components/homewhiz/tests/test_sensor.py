import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.sensor import generate_sensor_descriptions_from_config

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def washing_machine_config():
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "./fixtures/example_appliance_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_generate_descriptions_from_config(washing_machine_config):
    descriptions = generate_sensor_descriptions_from_config(washing_machine_config)
    keys = [d.key for d in descriptions]
    test_case.assertEqual(
        keys,
        [
            "SUB_STATE",
            "TEMPERATURE",
            "SPIN",
            "WASHER_DELAY",
            "WASHER_DURATION",
            "WASHER_REMAINING",
        ],
    )


def test_generic_washing_machine_on(washing_machine_config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000000a011e0c"
        "0000000080021102110000000000000000000000000000000100000000000001070000000000"
    )
    descriptions = generate_sensor_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "SUB_STATE": None,
            "SPIN": 1200,
            "TEMPERATURE": 30,
            "WASHER_DELAY": 0,
            "WASHER_DURATION": 137,
            "WASHER_REMAINING": 137,
        },
    )


def test_generic_washing_machine_running(washing_machine_config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c"
        "0080000080021100398080010000000000000000000080808100800000008001078000808000"
    )
    descriptions = generate_sensor_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "SUB_STATE": "WASHER_SUBSTATE_WASHING",
            "SPIN": 1200,
            "TEMPERATURE": 30,
            "WASHER_DELAY": 0,
            "WASHER_DURATION": 137,
            "WASHER_REMAINING": 57,
        },
    )


def test_generic_washing_machine_spinning(washing_machine_config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c"
        "00808080800211000a8080020000000000000000008080808180800000008081078000808000"
    )
    descriptions = generate_sensor_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "SUB_STATE": "WASHER_SUBSTATE_SPIN",
            "SPIN": 1200,
            "TEMPERATURE": 30,
            "WASHER_DELAY": 0,
            "WASHER_DURATION": 137,
            "WASHER_REMAINING": 10,
        },
    )


def test_generic_washing_machine_delay_defined(washing_machine_config):
    data = bytearray.fromhex(
        "003853e0ab0100000000000000000000000000000000000000000300000000000000000a01280e"
        "000000008002100210012c000000000000000000010000000100000000000001078000000000"
    )
    descriptions = generate_sensor_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "SUB_STATE": None,
            "SPIN": 1400,
            "TEMPERATURE": 40,
            "WASHER_DELAY": 104,
            "WASHER_DURATION": 136,
            "WASHER_REMAINING": 136,
        },
    )


def test_generic_washing_machine_delay_started(washing_machine_config):
    data = bytearray.fromhex(
        "003853e0ab0100000000000000000000000000000000000000000300000000000000003c01280e"
        "00000000800210021081ac080000000000000000010000000100000000000001078000808000"
    )
    descriptions = generate_sensor_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "SUB_STATE": "WASHER_SUBSTATE_TIME_DELAY_ENABLED",
            "SPIN": 1400,
            "TEMPERATURE": 40,
            "WASHER_DELAY": 104,
            "WASHER_DURATION": 136,
            "WASHER_REMAINING": 136,
        },
    )
