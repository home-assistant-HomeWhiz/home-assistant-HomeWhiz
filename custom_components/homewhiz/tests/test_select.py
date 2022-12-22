import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.select import generate_select_descriptions_from_config

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
    descriptions = generate_select_descriptions_from_config(washing_machine_config)
    keys = [d.key for d in descriptions]
    test_case.assertEqual(
        keys,
        [
            "STATE",
            "WASHER_PROGRAM",
            "WASHER_TEMPERATURE",
            "WASHER_SPIN",
            "WASHER_PREWASH",
            "WASHER_EXTRARINSE",
            "WASHER_FAST_PLUS",
            "WASHER_HIDDEN_ANTI_CREASE",
            "WASHER_STEAM",
            "WASHER_PHR",
        ],
    )


def test_generic_washing_machine_on(washing_machine_config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000000a011e0c"
        "0000000080021102110000000000000000000000000000000100000000000001070000000000"
    )
    descriptions = generate_select_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.get_option(data) for description in descriptions
    }

    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1200 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": "STEAM_OFF",
        },
    )


def test_generic_washing_machine_running(washing_machine_config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c"
        "0080000080021100398080010000000000000000000080808100800000008001078000808000"
    )
    descriptions = generate_select_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.get_option(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_RUNNING",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1200 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": "STEAM_OFF",
        },
    )


def test_generic_washing_machine_spinning(washing_machine_config):
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c"
        "00808080800211000a8080020000000000000000008080808180800000008081078000808000"
    )
    descriptions = generate_select_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.get_option(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_RUNNING",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": "1200 RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": "STEAM_OFF",
        },
    )


def test_generic_washing_machine_delay_defined(washing_machine_config):
    data = bytearray.fromhex(
        "003853e0ab0100000000000000000000000000000000000000000300000000000000000a01280e"
        "000000008002100210012c000000000000000000010000000100000000000001078000000000"
    )
    descriptions = generate_select_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.get_option(data) for description in descriptions
    }
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": "PROGRAM_COTTONS",
            "WASHER_SPIN": None,
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_STEAM": "STEAM_OFF",
        },
    )
