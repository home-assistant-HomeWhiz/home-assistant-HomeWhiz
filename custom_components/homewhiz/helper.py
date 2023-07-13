from __future__ import annotations

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS

from custom_components.homewhiz import IdExchangeResponse
from custom_components.homewhiz.api import ApplianceContents, ApplianceInfo
from custom_components.homewhiz.config_flow import EntryData


def build_entry_data(entry: ConfigEntry) -> EntryData:
    return EntryData(
        contents=from_dict(ApplianceContents, entry.data["contents"]),
        appliance_info=from_dict(ApplianceInfo, entry.data["appliance_info"])
        if entry.data["appliance_info"] is not None
        else None,
        ids=from_dict(IdExchangeResponse, entry.data["ids"]),
        cloud_config=None,
    )


def unit_for_key(key: str) -> str | None:
    if "temp" in key:
        return TEMP_CELSIUS
    if "spin" in key:
        return "RPM"
    return None


def icon_for_key(key: str) -> str | None:
    if "temp" in key:
        return "mdi:thermometer"
    if "spin" in key:
        return "mdi:rotate-3d-variant"
    return None
