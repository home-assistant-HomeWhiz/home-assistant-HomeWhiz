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
    file_path = os.path.join(dirname, "fixtures/example_ac_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_off(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x04\x1a\x00\x00\x00\x00\x1c\x00\x00\x14\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "AC": {
                "AIR_CONDITIONER_PROGRAM": "AIR_CONDITIONER_MODE_HEATING",
                "AIR_CONDITIONER_TARGET_TEMPERATURE": 26,
                "AIR_CONDITIONER_ROOM_TEMPERATURE": 28,
                "AIR_CONDITIONER_WIND_STRENGTH": "WIND_STRENGTH_LOW",
                "STATE": False,
            },
        },
    )


def test_mode_auto(config: ApplianceConfiguration) -> None:
    data = bytearray(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x06\x17\x03\x00\x00\x00\x1a\x00\x00\n\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    controls = generate_controls_from_config(config)
    values = {control.key: control.get_value(data) for control in controls}

    test_case.assertDictEqual(
        values,
        {
            "AC": {
                "AIR_CONDITIONER_PROGRAM": "AIR_CONDITIONER_MODE_AUTO",
                "AIR_CONDITIONER_TARGET_TEMPERATURE": 23,
                "AIR_CONDITIONER_ROOM_TEMPERATURE": 26,
                "AIR_CONDITIONER_WIND_STRENGTH": "WIND_STRENGTH_AUTO",
                "STATE": True,
            },
        },
    )
