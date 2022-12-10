import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.sensor import generate_descriptions_from_config


@pytest.fixture
def washing_machine_config():
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "./fixtures/example_appliance_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


@pytest.fixture
def ac_config():
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "./fixtures/example_ac_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_generate_descriptions_from_config(washing_machine_config):
    descriptions = generate_descriptions_from_config(washing_machine_config)
    keys = [d.key for d in descriptions]
    TestCase().assertEqual(
        keys,
        [
            "STATE",
            "SUB_STATE",
            "WASHER_PROGRAM",
            "TEMPERATURE",
            "WASHER_TEMPERATURE",
            "SPIN",
            "WASHER_SPIN",
            "WASHER_PREWASH",
            "WASHER_EXTRARINSE",
            "WASHER_FAST_PLUS",
            "WASHER_HIDDEN_ANTI_CREASE",
            "WASHER_STEAM",
            "WASHER_PHR",
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
    descriptions = generate_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case = TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "SUB_STATE": None,
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": None,
            "SPIN": 1200,
            "WASHER_SPIN": None,
            "TEMPERATURE": 30,
            "WASHER_STEAM": "STEAM_OFF",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
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
    descriptions = generate_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case = TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_RUNNING",
            "SUB_STATE": "WASHER_SUBSTATE_WASHING",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": None,
            "SPIN": 1200,
            "WASHER_SPIN": None,
            "TEMPERATURE": 30,
            "WASHER_STEAM": "STEAM_OFF",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
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
    descriptions = generate_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case = TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_RUNNING",
            "SUB_STATE": "WASHER_SUBSTATE_SPIN",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": None,
            "SPIN": 1200,
            "WASHER_SPIN": None,
            "TEMPERATURE": 30,
            "WASHER_STEAM": "STEAM_OFF",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
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
    descriptions = generate_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case = TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "SUB_STATE": None,
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": None,
            "SPIN": 1400,
            "WASHER_SPIN": None,
            "TEMPERATURE": 40,
            "WASHER_STEAM": "STEAM_OFF",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
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
    descriptions = generate_descriptions_from_config(washing_machine_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case = TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_TIME_DELAY_ACTIVE",
            "SUB_STATE": "WASHER_SUBSTATE_TIME_DELAY_ENABLED",
            "WASHER_EXTRARINSE": "EXTRA_RINSE_OFF",
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": "HIDDEN_ANTI_CREASE_OFF",
            "WASHER_PHR": "PHR_OFF",
            "WASHER_PREWASH": "PREWASH_OFF",
            "WASHER_PROGRAM": None,
            "SPIN": 1400,
            "WASHER_SPIN": None,
            "TEMPERATURE": 40,
            "WASHER_STEAM": "STEAM_OFF",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_DELAY": 104,
            "WASHER_DURATION": 136,
            "WASHER_REMAINING": 136,
        },
    )


def test_ac(ac_config):
    data = bytearray(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x04\x1a\x00\x00\x00\x00\x1c\x00\x00\x14\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    descriptions = generate_descriptions_from_config(ac_config)
    values = {
        description.key: description.value_fn(data) for description in descriptions
    }
    test_case = TestCase()
    test_case.maxDiff = None
    test_case.assertDictEqual(
        values,
        {
            "AIR_CONDITIONER_PROGRAM": None,
            "AIR_CONDITIONER_TARGET_TEMPERATURE": 26,
            "AIR_CONDITIONER_ROOM_TEMPERATURE": 28,
            "AIR_CONDITIONER_WIND_STRENGTH": "WIND_STRENGTH_LOW",
            "STATE": "DEVICE_STATE_OFF",
        },
    )
