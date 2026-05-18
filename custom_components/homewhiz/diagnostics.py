"""Diagnostics support for HomeWhiz Diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .bluetooth import HomewhizBluetoothUpdateCoordinator
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    # Get all entities for this config entry
    entity_registry = er.async_get(hass)
    entities_data: dict[str, dict[str, Any]] = {}

    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        entity_id = entity_entry.entity_id
        state = hass.states.get(entity_id)

        entity_info: dict[str, Any] = {
            "entity_id": entity_id,
            "unique_id": entity_entry.unique_id,
            "platform": entity_entry.platform,
            "original_name": entity_entry.original_name,
            "disabled": entity_entry.disabled,
            "translation_key": entity_entry.translation_key,
        }

        if state:
            entity_info["state"] = state.state
            entity_info["attributes"] = dict(state.attributes)

        entities_data[entity_id] = entity_info

    appliance_info = entry.data.get("appliance_info") or {}
    redacted_appliance_info = {
        **appliance_info,
        "applianceSerialNumber": "**REDACTED**",
    }

    result: dict[str, Any] = {
        "data": entry.data["contents"],
        "appliance_info": redacted_appliance_info,
        "entities": entities_data,
    }

    # Include BLE RSSI for Bluetooth appliances.
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(coordinator, HomewhizBluetoothUpdateCoordinator):
        service_info = bluetooth.async_last_service_info(
            hass, coordinator.address, connectable=True
        )
        result["bt_rssi"] = service_info.rssi if service_info else None

    return result
