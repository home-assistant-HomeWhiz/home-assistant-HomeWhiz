from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance_controls import WriteBooleanControl, generate_controls_from_config
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class HomeWhizSwitchEntity(HomeWhizEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: WriteBooleanControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control

    @property
    def is_on(self) -> bool | None:
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.send_command(self._control.set_value(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.send_command(self._control.set_value(False))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(data.contents.config)
    write_enum_controls = [c for c in controls if isinstance(c, WriteBooleanControl)]
    _LOGGER.debug(f"Switches: {[c.key for c in write_enum_controls]}")
    async_add_entities(
        [
            HomeWhizSwitchEntity(coordinator, control, entry.title, data)
            for control in write_enum_controls
        ]
    )
