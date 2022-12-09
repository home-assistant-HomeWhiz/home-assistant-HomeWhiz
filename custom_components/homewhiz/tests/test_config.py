import json
import os

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration

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
    # config fetched from the api
    "example_appliance_config.json",
]


@pytest.mark.parametrize("file_name", file_names)
def test_all_configs(file_name: str):
    dirname = os.path.dirname(__file__)
    file_path = os.path.join(dirname, f"./fixtures/{file_name}")

    with open(file_path) as file:
        json_content = json.load(file)
        from_dict(ApplianceConfiguration, json_content)
