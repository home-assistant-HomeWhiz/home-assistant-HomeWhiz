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
    file_path = os.path.join(dirname, "fixtures/example_washing_machine_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_on(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000000a011e0c"
        "0000000080021102110000000000000000000000000000000100000000000001070000000000"
    )
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}

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
            "WASHER_SPIN": "1200RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 137,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 137,
            "REMOTE_CONTROL": False,
            "WASHER_WARNING_DOOR_IS_OPEN": False,
            "WASHER_WARNING_NO_WATER": False,
            "WASHER_WARNING_SECURITY": False,
            "SETTINGS_VOLUME": "VOLUME_LOW",
            "WASHER_SOAKING": False,
            "WASHER_NIGHT": False,
            "WASHER_EXTRA_RINSE_COUNT": 0,
            "WASHER_ANTICREASE": False,
            "WASHER_ADD_WATER": False,
            "CUSTOM_DURATION_LEVEL": "DURATION_LEVEL_0",
        },
    )


def test_running(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c"
        "0080000080021100398080010000000000000000000080808100800000008001078000808000"
    )
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}
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
            "WASHER_SPIN": "1200RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 137,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 57,
            "REMOTE_CONTROL": False,
            "WASHER_WARNING_DOOR_IS_OPEN": False,
            "WASHER_WARNING_NO_WATER": False,
            "WASHER_WARNING_SECURITY": False,
            "SETTINGS_VOLUME": "VOLUME_LOW",
            "WASHER_SOAKING": False,
            "WASHER_NIGHT": False,
            "WASHER_EXTRA_RINSE_COUNT": 0,
            "WASHER_ANTICREASE": False,
            "WASHER_ADD_WATER": False,
            "CUSTOM_DURATION_LEVEL": "DURATION_LEVEL_0",
        },
    )


def test_spinning(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c"
        "00808080800211000a8080020000000000000000008080808180800000008081078000808000"
    )
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}
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
            "WASHER_SPIN": "1200RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_30",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 137,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 10,
            "REMOTE_CONTROL": False,
            "WASHER_WARNING_DOOR_IS_OPEN": False,
            "WASHER_WARNING_NO_WATER": False,
            "WASHER_WARNING_SECURITY": False,
            "SETTINGS_VOLUME": "VOLUME_LOW",
            "WASHER_SOAKING": False,
            "WASHER_NIGHT": False,
            "WASHER_EXTRA_RINSE_COUNT": 0,
            "WASHER_ANTICREASE": False,
            "WASHER_ADD_WATER": False,
            "CUSTOM_DURATION_LEVEL": "DURATION_LEVEL_0",
        },
    )


def test_delay_defined(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "003853e0ab0100000000000000000000000000000000000000000300000000000000000a01280e"
        "000000008002100210012c000000000000000000010000000100000000000001078000000000"
    )
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}
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
            "WASHER_SPIN": "1400RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_STEAM": False,
            "WASHER_REMAINING": 136,
            "WASHER_DELAY": 104,
            "WASHER_DURATION": 136,
            "REMOTE_CONTROL": False,
            "WASHER_WARNING_DOOR_IS_OPEN": True,
            "WASHER_WARNING_NO_WATER": False,
            "WASHER_WARNING_SECURITY": False,
            "SETTINGS_VOLUME": "VOLUME_LOW",
            "WASHER_SOAKING": False,
            "WASHER_NIGHT": False,
            "WASHER_EXTRA_RINSE_COUNT": 0,
            "WASHER_ANTICREASE": False,
            "WASHER_ADD_WATER": False,
            "CUSTOM_DURATION_LEVEL": "DURATION_LEVEL_0",
        },
    )


def test_warning(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00/JE\xa1\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00(\x07(\x08\x00\x00"
        b"\x80\x00\x00\x02\x06\x02\x06\x80\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        b"\x81\x00\x00\x01\x80\x80\x00\x00\x00\x00\x01\x07\x00\x00\x00\x00\x00"
    )

    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_PAUSED",
            "SUB_STATE": None,
            "WASHER_EXTRARINSE": False,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": False,
            "WASHER_PHR": False,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": "PROGRAM_MIX",
            "WASHER_SPIN": "800RPM",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_STEAM": False,
            "WASHER_REMAINING": 126,
            "WASHER_DELAY": 0,
            "WASHER_DURATION": 126,
            "REMOTE_CONTROL": False,
            "WASHER_WARNING_DOOR_IS_OPEN": True,
            "WASHER_WARNING_NO_WATER": False,
            "WASHER_WARNING_SECURITY": False,
            "SETTINGS_VOLUME": "VOLUME_LOW",
            "WASHER_SOAKING": False,
            "WASHER_NIGHT": False,
            "WASHER_EXTRA_RINSE_COUNT": 0,
            "WASHER_ANTICREASE": False,
            "WASHER_ADD_WATER": True,
            "CUSTOM_DURATION_LEVEL": "DURATION_LEVEL_0",
        },
    )


def test_remote_control_custom_settings(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00/JE\xa1\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\xaa\x00"
        b"\x00\n\x07(\x11\x00\x00\x81\x01\x00\x015\x015\x00\x00\x00\x00\x00"
        b"\x00\x00\x01\x00\x00\x00\x00\x81\x00\x00\x01\x80\x80\x00\x00\x00"
        b"\x00\x01\x07\x00\x00\x00\x01\x00"
    )

    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "STATE": "DEVICE_STATE_ON",
            "SUB_STATE": None,
            "WASHER_EXTRARINSE": True,
            "WASHER_FAST_PLUS": "FAST_PLUS_OFF",
            "WASHER_HIDDEN_ANTI_CREASE": False,
            "WASHER_PHR": False,
            "WASHER_PREWASH": False,
            "WASHER_PROGRAM": "PROGRAM_MIX",
            "WASHER_SPIN": "SPIN_RINSE_HOLD",
            "WASHER_TEMPERATURE": "TEMPERATURE_40",
            "WASHER_STEAM": False,
            "WASHER_DURATION": 113,
            "WASHER_DELAY": 0,
            "WASHER_REMAINING": 113,
            "REMOTE_CONTROL": True,
            "WASHER_WARNING_DOOR_IS_OPEN": False,
            "WASHER_WARNING_NO_WATER": False,
            "WASHER_WARNING_SECURITY": False,
            "SETTINGS_VOLUME": "VOLUME_HIGH",
            "WASHER_SOAKING": False,
            "WASHER_NIGHT": True,
            "WASHER_EXTRA_RINSE_COUNT": 1,
            "WASHER_ANTICREASE": False,
            "WASHER_ADD_WATER": True,
            "CUSTOM_DURATION_LEVEL": "DURATION_LEVEL_0",
        },
    )
