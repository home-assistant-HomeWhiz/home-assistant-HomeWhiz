import asyncio
import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from dacite import from_dict
from dacite.exceptions import WrongTypeError

from custom_components.homewhiz import api
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
    # Sparse refrigerator config from issue #375 (enum option without wifiArrayValue)
    "refrigerator-375.json",
]


@pytest.fixture
def fetch_config(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, Any]], api.ApplianceContents]:
    """Exercise the real parser with only the network calls mocked."""
    contents_index = api.ContentsIndexResponse(
        results=[api.ContentsDescription("test", "CONFIGURATION", 1, "en-GB")]
    )
    monkeypatch.setattr(
        api, "fetch_contents_index", AsyncMock(return_value=contents_index)
    )
    monkeypatch.setattr(api, "fetch_localizations", AsyncMock(return_value={}))

    def fetch(payload: dict[str, Any]) -> api.ApplianceContents:
        monkeypatch.setattr(
            api, "make_get_contents_request", AsyncMock(return_value=payload)
        )
        return asyncio.run(
            api.fetch_appliance_contents(api.LoginResponse("", "", "", 0), "test")
        )

    return fetch


@pytest.mark.parametrize("file_name", file_names)
def test_all_configs(
    file_name: str, fetch_config: Callable[[dict[str, Any]], api.ApplianceContents]
) -> None:
    file_path = Path(__file__).parent / "fixtures" / file_name
    with file_path.open() as file:
        json_content = json.load(file)
    expected = from_dict(ApplianceConfiguration, json_content)
    config = fetch_config(json_content).config
    assert config == expected
    generate_controls_from_config(f"test_config_{file_name}", config)


@pytest.mark.parametrize(
    ("str_key", "expected_value"),
    [(0, "0"), (7, "7"), ("0", "0"), ("DRYER_LEVEL", "dryer_level")],
)
def test_fetch_config_with_integer_enum_str_key(
    fetch_config: Callable[[dict[str, Any]], api.ApplianceContents],
    str_key: str | int,
    expected_value: str,
) -> None:
    """Issue #451: a numeric enum label must not prevent appliance setup."""
    contents = fetch_config(
        {
            "subPrograms": [
                {
                    "strKey": "DRYER_DRYING_LEVEL",
                    "wifiArrayIndex": 1,
                    "enumValues": [{"strKey": str_key, "wifiArrayValue": 0}],
                }
            ]
        }
    )

    assert contents.config.subPrograms is not None
    assert contents.config.subPrograms[0].enumValues is not None
    assert contents.config.subPrograms[0].enumValues[0].strKey == str(str_key)
    controls = generate_controls_from_config(f"issue_451_{str_key!r}", contents.config)
    control = next(c for c in controls if c.key == "dryer_drying_level")
    assert control.get_value(bytearray([0, 0])) == expected_value
    # Config entries persist these contents and parse them again on setup.
    assert from_dict(api.ApplianceContents, asdict(contents)) == contents


@pytest.mark.parametrize("str_key", [None, True, 0.5, [], {}])
def test_fetch_config_rejects_other_enum_str_key_types(
    fetch_config: Callable[[dict[str, Any]], api.ApplianceContents], str_key: Any
) -> None:
    with pytest.raises(WrongTypeError, match=r"subPrograms\.enumValues\.strKey"):
        fetch_config(
            {
                "subPrograms": [
                    {"wifiArrayIndex": 1, "enumValues": [{"strKey": str_key}]}
                ]
            }
        )


def test_fetch_config_does_not_cast_other_string_fields(
    fetch_config: Callable[[dict[str, Any]], api.ApplianceContents],
) -> None:
    with pytest.raises(WrongTypeError, match=r"subPrograms\.strKey"):
        fetch_config({"subPrograms": [{"strKey": 0, "wifiArrayIndex": 1}]})


@pytest.mark.parametrize(
    "payload",
    [{}, {"subPrograms": None}, {"subPrograms": [{"wifiArrayIndex": 1}]}],
)
def test_fetch_config_preserves_optional_fields(
    fetch_config: Callable[[dict[str, Any]], api.ApplianceContents],
    payload: dict[str, Any],
) -> None:
    expected = from_dict(ApplianceConfiguration, payload)
    assert fetch_config(payload).config == expected
