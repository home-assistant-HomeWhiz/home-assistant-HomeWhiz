import datetime
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
    controls = generate_controls_from_config("test_washing_machine_test_on", config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_on",
            "sub_state": None,
            "washer_extrarinse": False,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": False,
            "washer_phr": False,
            "washer_prewash": False,
            "washer_program": "program_cottons",
            "washer_spin": "1200rpm",
            "washer_temperature": "temperature_30",
            "washer_steam": False,
            "washer_duration": 137,
            "washer_delay": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=137),
            "washer_remaining": 137,
            "remote_control": False,
            "washer_warning_door_is_open": False,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_low",
            "washer_soaking": False,
            "washer_night": False,
            "washer_extra_rinse_count": 0,
            "washer_anticrease": False,
            "washer_add_water": False,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 0,
            "delay_start_time#0": None,
        },
    )


def test_running(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c"
        "0080000080021100398080010000000000000000000080808100800000008001078000808000"
    )
    controls = generate_controls_from_config(
        "test_washing_machine_test_running", config
    )
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_running",
            "sub_state": "washer_substate_washing",
            "washer_extrarinse": False,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": False,
            "washer_phr": False,
            "washer_prewash": False,
            "washer_program": "program_cottons",
            "washer_spin": "1200rpm",
            "washer_temperature": "temperature_30",
            "washer_steam": False,
            "washer_duration": 137,
            "washer_delay": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=57),
            "washer_remaining": 57,
            "remote_control": False,
            "washer_warning_door_is_open": False,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_low",
            "washer_soaking": False,
            "washer_night": False,
            "washer_extra_rinse_count": 0,
            "washer_anticrease": False,
            "washer_add_water": False,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 0,
            "delay_start_time#0": None,
        },
    )


def test_spinning(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c"
        "00808080800211000a8080020000000000000000008080808180800000008081078000808000"
    )
    controls = generate_controls_from_config(
        "test_washing_machine_test_spinning", config
    )
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_running",
            "sub_state": "washer_substate_spin",
            "washer_extrarinse": False,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": False,
            "washer_phr": False,
            "washer_prewash": False,
            "washer_program": "program_cottons",
            "washer_spin": "1200rpm",
            "washer_temperature": "temperature_30",
            "washer_steam": False,
            "washer_duration": 137,
            "washer_delay": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=10),
            "washer_remaining": 10,
            "remote_control": False,
            "washer_warning_door_is_open": False,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_low",
            "washer_soaking": False,
            "washer_night": False,
            "washer_extra_rinse_count": 0,
            "washer_anticrease": False,
            "washer_add_water": False,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 0,
            "delay_start_time#0": None,
        },
    )


def test_delay_defined(config: ApplianceConfiguration) -> None:
    data = bytearray.fromhex(
        "003853e0ab0100000000000000000000000000000000000000000300000000000000000a01280e"
        "000000008002100210012c000000000000000000010000000100000000000001078000000000"
    )
    controls = generate_controls_from_config(
        "test_washing_machine_test_delayed", config
    )
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_on",
            "sub_state": None,
            "washer_extrarinse": False,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": False,
            "washer_phr": False,
            "washer_prewash": False,
            "washer_program": "program_cottons",
            "washer_spin": "1400rpm",
            "washer_temperature": "temperature_40",
            "washer_steam": False,
            "washer_remaining": 136,
            "washer_delay": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=104 + 136),
            "washer_duration": 136,
            "remote_control": False,
            "washer_warning_door_is_open": True,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_low",
            "washer_soaking": False,
            "washer_night": False,
            "washer_extra_rinse_count": 0,
            "washer_anticrease": False,
            "washer_add_water": False,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 104,
            "delay_start_time#0": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=104),
        },
    )


def test_warning(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00/JE\xa1\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00(\x07(\x08\x00\x00"
        b"\x80\x00\x00\x02\x06\x02\x06\x80\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        b"\x81\x00\x00\x01\x80\x80\x00\x00\x00\x00\x01\x07\x00\x00\x00\x00\x00"
    )

    controls = generate_controls_from_config(
        "test_washing_machine_test_warning", config
    )
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_paused",
            "sub_state": None,
            "washer_extrarinse": False,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": False,
            "washer_phr": False,
            "washer_prewash": False,
            "washer_program": "program_mix",
            "washer_spin": "800rpm",
            "washer_temperature": "temperature_40",
            "washer_steam": False,
            "washer_remaining": 126,
            "washer_delay": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=126),
            "washer_duration": 126,
            "remote_control": False,
            "washer_warning_door_is_open": True,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_low",
            "washer_soaking": False,
            "washer_night": False,
            "washer_extra_rinse_count": 0,
            "washer_anticrease": False,
            "washer_add_water": True,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 0,
            "delay_start_time#0": None,
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

    controls = generate_controls_from_config(
        "test_washing_machine_test_remote_control_custom_settings", config
    )
    values = {control.key: control.get_value(data) for control in controls}
    test_case.assertDictEqual(
        values,
        {
            "state": "device_state_on",
            "sub_state": None,
            "washer_extrarinse": True,
            "washer_fast_plus": "fast_plus_off",
            "washer_hidden_anti_crease": False,
            "washer_phr": False,
            "washer_prewash": False,
            "washer_program": "program_mix",
            "washer_spin": "spin_rinse_hold",
            "washer_temperature": "temperature_40",
            "washer_steam": False,
            "washer_duration": 113,
            "washer_delay": datetime.datetime.now(tz=datetime.UTC).replace(
                second=0, microsecond=0
            )
            + datetime.timedelta(minutes=113),
            "washer_remaining": 113,
            "remote_control": True,
            "washer_warning_door_is_open": False,
            "washer_warning_no_water": False,
            "washer_warning_security": False,
            "settings_volume": "volume_high",
            "washer_soaking": False,
            "washer_night": True,
            "washer_extra_rinse_count": 1,
            "washer_anticrease": False,
            "washer_add_water": True,
            "custom_duration_level": "duration_level_0",
            "delay_start#0": 0,
            "delay_start_time#0": None,
        },
    )
