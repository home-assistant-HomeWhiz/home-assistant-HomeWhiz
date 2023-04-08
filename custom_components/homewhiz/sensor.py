from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance_controls import (
    DebugControl,
    EnumControl,
    NumericControl,
    TimeControl,
    generate_controls_from_config,
)
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class HomeWhizSensorEntity(HomeWhizEntity, SensorEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: TimeControl | EnumControl | NumericControl | DebugControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control
        if isinstance(control, TimeControl):
            self._attr_icon = "mdi:clock-outline"
            self._attr_native_unit_of_measurement = "min"
            self._attr_device_class = SensorDeviceClass.DURATION
        if isinstance(control, EnumControl):
            self._attr_device_class = SensorDeviceClass.ENUM  # type:ignore
            self._attr_options = list(self._control.options.values())  # type:ignore

    @property
    def native_value(self) -> float | int | str | None:
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(data.contents.config)
    sensor_controls = [
        c
        for c in controls
        if isinstance(c, TimeControl)
        or isinstance(c, EnumControl)
        or isinstance(c, NumericControl)
        or isinstance(c, DebugControl)
    ]
    _LOGGER.debug(f"Sensors: {[c.key for c in sensor_controls]}")
    async_add_entities(
        [
            HomeWhizSensorEntity(coordinator, control, entry.title, data)
            for control in sensor_controls
        ]
    )
