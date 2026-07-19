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
    file_path = Path(__file__).parent / "fixtures" / "refrigerator-375.json"
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_fridge", config)
    control_keys = [control.key for control in controls]

    test_case.assertListEqual(
        control_keys,
        [
            "fridge_degree_dimension",
            "fridge_cooler_temperature",
            "fridge_freezer_temperature",
            "fridge_quick_cool",
            "fridge_freezer_joker_mode",
            "fridge_freezer_joker_temperature",
            "fridge_a_cool",
            "fridge_warning_door_is_open",
            "fridge_warning_high_temperature",
            "settings_door_alarm_time",
        ],
    )
