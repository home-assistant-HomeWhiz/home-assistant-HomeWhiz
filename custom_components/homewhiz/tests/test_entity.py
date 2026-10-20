"""Tests for the device info built in entity.py (hass-free, like the others)."""

from unittest.mock import Mock

from custom_components.homewhiz.api import ApplianceContents
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.const import DOMAIN
from custom_components.homewhiz.entity import build_device_info


def _entry_data(name: str | None) -> EntryData:
    info = Mock(brand=3, model="7188239270") if name is not None else None
    if info is not None:
        info.name = name
    return EntryData(
        ids=Mock(),
        contents=ApplianceContents(config=Mock(), localization={}),
        appliance_info=info,
        cloud_config=None,
    )


def test_trailing_space_of_the_api_name_is_not_shown() -> None:
    info = build_device_info("Trockner ", _entry_data("Trockner "))
    assert info["name"] == "Trockner"


def test_identifiers_keep_the_trailing_space() -> None:
    # Changing them would orphan the entities of every existing entry.
    info = build_device_info("Trockner ", _entry_data("Trockner "))
    assert info["identifiers"] == {(DOMAIN, "Trockner ")}


def test_clean_name_is_unchanged() -> None:
    info = build_device_info("Trockner", _entry_data("Trockner"))
    assert info["name"] == "Trockner"


def test_fallback_name_without_appliance_info_is_stripped_too() -> None:
    info = build_device_info("Waschmaschine ", _entry_data(None))
    assert info["name"] == "Waschmaschine"
    assert info["identifiers"] == {(DOMAIN, "Waschmaschine ")}
