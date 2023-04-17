from __future__ import annotations

import logging

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS

from custom_components.homewhiz import IdExchangeResponse
from custom_components.homewhiz.api import ApplianceContents, ApplianceInfo
from custom_components.homewhiz.config_flow import EntryData

_LOGGER: logging.Logger = logging.getLogger(__package__)


def build_entry_data(entry: ConfigEntry) -> EntryData:
    _LOGGER.debug("Using config entry for building entry data %s", ConfigEntry)
    return EntryData(
        contents=from_dict(ApplianceContents, entry.data["contents"]),
        appliance_info=from_dict(ApplianceInfo, entry.data["appliance_info"])
        if entry.data["appliance_info"] is not None
        else None,
        ids=from_dict(IdExchangeResponse, entry.data["ids"]),
        cloud_config=None,
    )


def unit_for_key(key: str) -> str | None:
    if "TEMP" in key:
        return TEMP_CELSIUS
    if "SPIN" in key:
        return "RPM"
    return None


def icon_for_key(key: str) -> str | None:
    if "TEMP" in key:
        return "mdi:thermometer"
    if "SPIN" in key:
        return "mdi:rotate-3d-variant"
    return None
