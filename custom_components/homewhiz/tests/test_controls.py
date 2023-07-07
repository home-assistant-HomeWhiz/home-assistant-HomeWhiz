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
    controls = generate_controls_from_config(config)
    controls_map = {control.key: control for control in controls}
    assert "WASHER_TEMPERATURE" in controls_map
    temp_control = controls_map["WASHER_TEMPERATURE"]
    assert isinstance(temp_control, EnumControl)
    test_case.assertListEqual(
        list(temp_control.options.values()),
        [
            "TEMPERATURE_COLD_WASH",
            "TEMPERATURE_20",
            "TEMPERATURE_30",
            "TEMPERATURE_40",
            "60C",
            "90C",
        ],
    )
