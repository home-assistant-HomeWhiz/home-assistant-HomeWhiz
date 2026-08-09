import json
from pathlib import Path
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import generate_controls_from_config

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def config() -> ApplianceConfiguration:
    file_path = Path(__file__).parent / "fixtures" / "beko-hob.json"
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_hob", config)
    control_keys = [control.key for control in controls]

    test_case.assertListEqual(
        control_keys,
        [
            "state",
            "monitoring_hob2hood",
            "settings_hob2hood",
            "settings_keylocked",
            "zone_1_program",
            "zone_1_hob_predefined_program",
            "zone_1_hob_heater_level",
            "zone_1_hob_flexi",
            "zone_1_zone_extended",
            "zone_1_cooking_state",
            "zone_1_duration",
            "zone_1_hob_hot",
            "zone_1_hob_pan_info",
            "zone_2_program",
            "zone_2_hob_predefined_program",
            "zone_2_hob_heater_level",
            "zone_2_hob_flexi",
            "zone_2_zone_extended",
            "zone_2_cooking_state",
            "zone_2_duration",
            "zone_2_hob_hot",
            "zone_2_hob_pan_info",
            "zone_3_program",
            "zone_3_hob_predefined_program",
            "zone_3_hob_heater_level",
            "zone_3_hob_flexi",
            "zone_3_zone_extended",
            "zone_3_cooking_state",
            "zone_3_duration",
            "zone_3_hob_hot",
            "zone_3_hob_pan_info",
            "zone_4_program",
            "zone_4_hob_predefined_program",
            "zone_4_hob_heater_level",
            "zone_4_hob_flexi",
            "zone_4_zone_extended",
            "zone_4_cooking_state",
            "zone_4_duration",
            "zone_4_hob_hot",
            "zone_4_hob_pan_info",
        ],
    )
