import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.homewhiz import DOMAIN
from custom_components.homewhiz.appliance_controls import (
    BooleanCompareControl,
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
    def is_on(self) -> bool | None:  # type: ignore[override]
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(entry.entry_id, data.contents.config)
    boolean_controls = [
        c
        for c in controls
        if isinstance(c, BooleanControl) and not isinstance(c, WriteBooleanControl)
    ]

    # AUTO mode status for Arcelik ADE 607-2 cooker hood.
    info = data.appliance_info
    if (
        info is not None
        and info.model == "7704331217"
        and info.applianceType == 8
    ):
        boolean_controls.append(
            BooleanCompareControl(
                key="hood_auto_mode",
                read_index=44,
                compare_value=1,
            )
        )

    _LOGGER.debug("Binary sensors: %s", [c.key for c in boolean_controls])
    async_add_entities(
        [
            HomeWhizBinarySensorEntity(coordinator, control, entry.title, data)
            for control in boolean_controls
        ]
    )
