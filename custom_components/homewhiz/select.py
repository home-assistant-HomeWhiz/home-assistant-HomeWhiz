from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance_controls import (
    WriteEnumControl,
    WriteNumericControl,
    generate_controls_from_config,
    get_bounded_values_options,
)
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class NumericControlAsEnum(WriteEnumControl):
    def __init__(self, numeric_control: WriteNumericControl):
        super().__init__(
            key=numeric_control.key,
            read_index=numeric_control.read_index,
            write_index=numeric_control.write_index,
            options=get_bounded_values_options(
                numeric_control.key, numeric_control.bounds
            ),
        )


class HomeWhizSelectEntity(HomeWhizEntity, SelectEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: WriteEnumControl | WriteNumericControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = (
            NumericControlAsEnum(control)
            if isinstance(control, WriteNumericControl)
            else control
        )
        self._attr_options = list(self._control.options.values())

    @property
    def current_option(self) -> str | None:  # type: ignore[override]
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.send_command(self._control.set_value(option))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(entry.entry_id, data.contents.config)
    write_enum_controls = [
        c for c in controls if isinstance(c, (WriteEnumControl, WriteNumericControl))
    ]
    _LOGGER.debug(f"Selects: {[c.key for c in write_enum_controls]}")
    async_add_entities(
        [
            HomeWhizSelectEntity(coordinator, control, entry.title, data)
            for control in write_enum_controls
        ]
    )
