import json
import os
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    EnumControl,
    generate_controls_from_config,
)

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def config() -> ApplianceConfiguration:
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, "fixtures/example_washing_machine_config.json")
    with open(file_path) as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_options_order(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_controls", config)
    controls_map = {control.key: control for control in controls}
    assert "washer_temperature" in controls_map
    temp_control = controls_map["washer_temperature"]
    assert isinstance(temp_control, EnumControl)
    test_case.assertListEqual(
        list(temp_control.options.values()),
        [
            "temperature_cold_wash",
            "temperature_20",
            "temperature_30",
            "temperature_40",
            "60c",
            "90c",
        ],
    )
