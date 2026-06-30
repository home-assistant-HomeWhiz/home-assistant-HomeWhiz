from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance_controls import WriteTimeControl, generate_controls_from_config
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

# The appliance stores the delay in one byte for hours and one for minutes, so the
# largest value it can represent is 23h59m. Expressed in minutes for a single unit.
MAX_DELAY_MINUTES = 23 * 60 + 59


class HomeWhizNumberEntity(HomeWhizEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_DELAY_MINUTES
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: WriteTimeControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control
        # Override the per-entity translation device_class set by HomeWhizEntity with
        # the standard duration device class.
        self._attr_device_class = NumberDeviceClass.DURATION

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        for command in self._control.set_value(int(value)):
            await self.coordinator.send_command(command)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(entry.entry_id, data.contents.config)
    number_controls = [c for c in controls if isinstance(c, WriteTimeControl)]
    _LOGGER.debug("Numbers: %s", [c.key for c in number_controls])
    async_add_entities(
        [
            HomeWhizNumberEntity(coordinator, control, entry.title, data)
            for control in number_controls
        ]
    )
