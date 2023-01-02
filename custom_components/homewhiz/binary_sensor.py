import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.homewhiz import DOMAIN
from custom_components.homewhiz.appliance_controls import (
    BooleanControl,
    WriteBooleanControl,
    generate_controls_from_config,
)
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.entity import HomeWhizEntity
from custom_components.homewhiz.helper import build_entry_data
from custom_components.homewhiz.homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class HomeWhizBinarySensorEntity(HomeWhizEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: BooleanControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(data.contents.config)
    boolean_controls = [
        c
        for c in controls
        if isinstance(c, BooleanControl) and not isinstance(c, WriteBooleanControl)
    ]
    _LOGGER.debug(f"Binary sensors: {[c.key for c in boolean_controls]}")
    async_add_entities(
        [
            HomeWhizBinarySensorEntity(coordinator, control, entry.title, data)
            for control in boolean_controls
        ]
    )
