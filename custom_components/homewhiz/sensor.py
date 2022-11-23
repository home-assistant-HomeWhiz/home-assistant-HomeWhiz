from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomewhizDataUpdateCoordinator
from .const import DOMAIN, COORDINATORS
from .homewhiz import WasherState

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass
class HomeWhizEntityDescription(SensorEntityDescription):
    value_fn: Callable[[WasherState], float | str] | None = None


DESCRIPTIONS: List[HomeWhizEntityDescription] = [
    HomeWhizEntityDescription(
        device_class=SensorDeviceClass.TEMPERATURE,
        key="temperature",
        name="Temperature",
        value_fn=lambda s: s.temperature,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    HomeWhizEntityDescription(
        key="spin",
        name="Spin",
        icon="mdi:rotate-3d-variant",
        value_fn=lambda s: s.spin,
        native_unit_of_measurement="rpm",
    ),
    HomeWhizEntityDescription(
        key="state",
        name="State",
        icon="mdi:state-machine",
        value_fn=lambda s: s.device_state.name,
    ),
    HomeWhizEntityDescription(
        key="sub-state",
        name="Sub-state",
        icon="mdi:state-machine",
        value_fn=lambda s: s.device_sub_state.name,
    ),
    HomeWhizEntityDescription(
        key="rinse-hold",
        name="Rinse and hold",
        icon="mdi:water",
        value_fn=lambda s: s.rinse_hold,
    ),
    HomeWhizEntityDescription(
        key="duration",
        name="Duration",
        icon="mdi:clock-outline",
        value_fn=lambda s: s.duration_minutes,
        native_unit_of_measurement="min",
    ),
    HomeWhizEntityDescription(
        key="remaining",
        name="Time remaining",
        icon="mdi:clock-outline",
        value_fn=lambda s: s.remaining_minutes,
        native_unit_of_measurement="min",
    ),
    HomeWhizEntityDescription(
        key="delay",
        name="Delay",
        icon="mdi:clock-outline",
        value_fn=lambda s: s.delay_minutes,
        native_unit_of_measurement="min",
    ),
]


class HomeWhizEntity(CoordinatorEntity[WasherState], SensorEntity):
    def __init__(
        self,
        coordinator: HomewhizDataUpdateCoordinator,
        description: HomeWhizEntityDescription,
    ):
        super().__init__(coordinator)
        short_mac = coordinator.client.address.split("-")[-1]
        self.entity_description = description
        self._value_fn = description.value_fn
        self._attr_unique_id = f"{short_mac}_{description.key}"
        self._attr_name = f"{short_mac} {description.name}"
        _LOGGER.debug(self._attr_unique_id)
        self._attr_device_info = DeviceInfo(
            connections={("bluetooth", coordinator.client.address)},
            identifiers={(DOMAIN, short_mac)},
            name=short_mac,
        )

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        return self._value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators = hass.data[DOMAIN][COORDINATORS]
    async_add_entities(
        [
            HomeWhizEntity(coordinator, description)
            for coordinator in coordinators
            for description in DESCRIPTIONS
        ]
    )
