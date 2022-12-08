from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Callable, List

from dacite import from_dict
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
from .api import ApplianceContents, ApplianceInfo, IdExchangeResponse
from .appliance_config import (
    ApplianceConfiguration,
    ApplianceFeatureEnumOption,
    ApplianceProgram,
    ApplianceFeatureBoundedOption,
    ApplianceProgressFeature,
)
from .config_flow import EntryData
from .const import DOMAIN
from .homewhiz import brand_name_by_code

_LOGGER: logging.Logger = logging.getLogger(__package__)


def clamp(value: int):
    return value if value < 128 else value - 128


@dataclass
class HomeWhizEntityDescription(SensorEntityDescription):
    value_fn: Callable[[bytearray], float | str | None] | None = None


class EnumEntityDescription(HomeWhizEntityDescription):
    def __init__(
        self, key: str, options: List[ApplianceFeatureEnumOption], read_index: int
    ):
        self.key = key
        self.icon = "mdi:state-machine"
        self.options = options
        self._read_index = read_index
        self.device_class = f"{DOMAIN}__{self.key}"

    def value_fn(self, data):
        value = clamp(data[self._read_index])
        for option in self.options:
            if option.wifiArrayValue == value:
                return option.strKey
        return None


class ProgramEntityDescription(HomeWhizEntityDescription):
    def __init__(self, program: ApplianceProgram):
        self.key = program.strKey
        self.icon = "mdi:state-machine"
        self._program = program

    def value_fn(self, data):
        value = clamp(data[self._program.wifiArrayIndex])
        for option in self._program.values:
            if option.wfaValue is value:
                return option.strKey
        return None


class SubProgramBoundedEntityDescription(HomeWhizEntityDescription):
    def __init__(self, bounds: ApplianceFeatureBoundedOption, read_index: int):
        self.key = bounds.strKey
        self._bounds = bounds
        self._read_index = read_index

    def value_fn(self, data):
        return clamp(data[self._read_index]) * self._bounds.factor

    @property
    def native_unit_of_measurement(self):
        if "TEMP" in self.key:
            return TEMP_CELSIUS
        if "SPIN" in self.key:
            return "rpm"

    @property
    def icon(self):
        if "TEMP" in self.key:
            return "mdi:thermometer"
        if "SPIN" in self.key:
            return "mdi:rotate-3d-variant"


class ProgressEntityDescription(HomeWhizEntityDescription):
    def __init__(self, progress: ApplianceProgressFeature):
        self.key = progress.strKey
        self.icon = "mdi:clock-outline"
        self.native_unit_of_measurement = "min"
        self.device_class = SensorDeviceClass.DURATION
        self._progress = progress

    def value_fn(self, data):
        hours = clamp(data[self._progress.hour.wifiArrayIndex])
        minutes = (
            clamp(data[self._progress.minute.wifiArrayIndex])
            if self._progress.minute is not None
            else 0
        )
        return hours * 60 + minutes


def generate_descriptions_from_config(
    config: ApplianceConfiguration,
) -> List[HomeWhizEntityDescription]:
    result = []
    if config.deviceStates is not None:
        result.append(
            EnumEntityDescription(
                "STATE",
                config.deviceStates.states,
                config.deviceStates.wifiArrayReadIndex,
            )
        )
    if config.deviceSubStates is not None:
        result.append(
            EnumEntityDescription(
                "SUB_STATE",
                config.deviceSubStates.subStates,
                config.deviceSubStates.wifiArrayReadIndex,
            )
        )
    result.append(ProgramEntityDescription(config.program))
    for sub_program in config.subPrograms:
        read_index = sub_program.wifiArrayIndex
        if sub_program.boundedValues is not None:
            for bounds in sub_program.boundedValues:
                result.append(SubProgramBoundedEntityDescription(bounds, read_index))
        if sub_program.enumValues is not None:
            result.append(
                EnumEntityDescription(
                    sub_program.strKey, sub_program.enumValues, read_index
                )
            )
    if config.progressVariables is not None:
        for field in fields(config.progressVariables):
            feature = getattr(config.progressVariables, field.name)
            if feature is not None:
                result.append(
                    ProgressEntityDescription(feature),
                )
    return result


class HomeWhizEntity(CoordinatorEntity[HomewhizDataUpdateCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: HomewhizDataUpdateCoordinator,
        description: HomeWhizEntityDescription,
        entry: ConfigEntry,
        data: EntryData,
    ):
        super().__init__(coordinator)
        unique_name = entry.title
        friendly_name = (
            data.appliance_info.name if data.appliance_info is not None else unique_name
        )

        self._localization = data.contents.localization
        self.entity_description = description
        self._value_fn = description.value_fn
        self._attr_unique_id = f"{unique_name}_{description.key}"
        manufacturer = (
            brand_name_by_code[data.appliance_info.brand]
            if data.appliance_info is not None
            else None
        )
        model = data.appliance_info.model if data.appliance_info is not None else None
        self._attr_device_info = DeviceInfo(
            connections={("bluetooth", entry.unique_id)},
            identifiers={(DOMAIN, unique_name)},
            name=friendly_name,
            manufacturer=manufacturer,
            model=model,
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
        return (
            self.coordinator.connection is not None
            and self.coordinator.connection.is_connected
        )

    @property
    def name(self) -> str | None:
        key = self.entity_description.key
        if key == "STATE":
            return "State"
        if key == "SUB_STATE":
            return "Sub-state"
        for localization_key in self._localization:
            if localization_key == key:
                return self._localization[localization_key]
        return key


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = EntryData(
        contents=from_dict(ApplianceContents, entry.data["contents"]),
        appliance_info=from_dict(ApplianceInfo, entry.data["appliance_info"])
        if entry.data["appliance_info"] is not None
        else None,
        ids=from_dict(IdExchangeResponse, entry.data["ids"]),
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = generate_descriptions_from_config(data.contents.config)
    _LOGGER.debug(f"Entities: {[d.key for d in descriptions]}")
    async_add_entities(
        [
            HomeWhizEntity(coordinator, description, entry, data)
            for description in descriptions
        ]
    )
