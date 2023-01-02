import json
import os

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import generate_controls_from_config

file_names = [
    # Configs extracted from the original app
    "7127441700-washer.json",
    "7152640100-washer.json",
    "arcelik-dishwasher.json",
    "arcelik-dryer.json",
    "arcelik-oven.json",
    "arcelik-refrigerator.json",
    "arcelik-washer.json",
    "deneme.json",
    "dryer-arwen.json",
    "dryer-e2e.json",
    "grundig-dishwasher.json",
    "grundig-dryer.json",
    "grundig-oven.json",
    "grundig-refrigerator.json",
    "grundig-washer.json",
    "oven-meat-probe.json",
    "oven-multi.json",
    "oven-pirolitik.json",
    # configs fetched from the api
    "example_washing_machine_config.json",
    "example_ac_config.json",
    "example_ac_advanced_config.json",
    "example_oven_config.json",
    "example_dishwasher_config.json",
    "example_washing_machine_with_dryer_config.json",
]


@pytest.mark.parametrize("file_name", file_names)
def test_all_configs(file_name: str) -> None:
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, f"./fixtures/{file_name}")

    with open(file_path) as file:
        json_content = json.load(file)
        config = from_dict(ApplianceConfiguration, json_content)
        generate_controls_from_config(config)
