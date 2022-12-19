from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from dacite import from_dict
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import ApplianceContents, ApplianceInfo, IdExchangeResponse
from .appliance_config import (
    ApplianceConfiguration,
    ApplianceFeature,
    ApplianceFeatureBoundedOption,
    ApplianceFeatureEnumOption,
    ApplianceProgram,
)
from .config_flow import EntryData
from .const import DOMAIN
from .homewhiz import HomewhizCoordinator, brand_name_by_code

_LOGGER: logging.Logger = logging.getLogger(__package__)


def clamp(value: int):
    return value if value < 128 else value - 128


@dataclass
class HomeWhizEntitySelectDescription(SelectEntityDescription):
    read_index: int | None = None
    write_index: int | None = None

    byte_to_option: Callable[[int], float | str | None] | None = None
    option_to_byte: Callable[[str], int] | None = None


class EnumEntityDescription(HomeWhizEntitySelectDescription):
    def __init__(
        self,
        key: str,
        options: list[ApplianceFeatureEnumOption],
        read_index: int,
        write_index: int,
    ):
        self.key = key
        self.icon = "mdi:state-machine"
        self.enum_options = options
        self.options = [option.strKey for option in options]
        self.read_index = read_index
        self.write_index = write_index
        _LOGGER.debug(f"{key}: {write_index}")
        self.device_class = f"{DOMAIN}__{self.key}"

    def byte_to_option(self, byte):
        for option in self.enum_options:
            if option.wifiArrayValue == byte:
                return option.strKey
        return None

    def option_to_byte(self, value):
        for option in self.enum_options:
            if option.strKey == value:
                return option.wifiArrayValue
        return None


class ProgramEntityDescription(EnumEntityDescription):
    def __init__(self, program: ApplianceProgram):
        super().__init__(
            program.strKey,
            program.values,
            program.wifiArrayIndex,
            program.wfaWriteIndex
            if program.wfaWriteIndex is not None
            else program.wifiArrayIndex,
        )


class SubProgramBoundedEntityDescription(HomeWhizEntitySelectDescription):
    def __init__(
        self,
        parent_key: str,
        bounds: ApplianceFeatureBoundedOption,
        read_index: int,
        write_index: int,
    ):
        self.key = bounds.strKey if bounds.strKey else parent_key
        self._bounds = bounds
        self.read_index = read_index
        self.write_index = write_index
        self.options = [
            str(num)
            for num in range(bounds.lowerLimit, bounds.upperLimit + 1, bounds.step)
        ]

    def byte_to_option(self, value):
        return value * self._bounds.factor

    def option_to_byte(self, value):
        return int(value)

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


def generate_descriptions_from_features(features: list[ApplianceFeature]):
    result = []
    for feature in features:
        read_index = feature.wifiArrayIndex
        write_index = (
            feature.wfaWriteIndex
            if feature.wfaWriteIndex is not None
            else feature.wifiArrayIndex
        )
        if feature.boundedValues is not None:
            for bounds in feature.boundedValues:
                result.append(
                    SubProgramBoundedEntityDescription(
                        feature.strKey, bounds, read_index, write_index
                    )
                )
        if feature.enumValues is not None:
            result.append(
                EnumEntityDescription(
                    feature.strKey,
                    feature.enumValues,
                    read_index,
                    write_index,
                )
            )
    return result


def generate_descriptions_from_config(
    config: ApplianceConfiguration,
) -> list[HomeWhizEntitySelectDescription]:
    _LOGGER.debug("Generating descriptions from config")
    result = []
    if config.deviceStates is not None:
        _LOGGER.debug("Adding STATE EnumEntityDescription")
        result.append(
            EnumEntityDescription(
                "STATE",
                config.deviceStates.states,
                config.deviceStates.wifiArrayReadIndex,
                config.deviceStates.wifiArrayWriteIndex
                if config.deviceStates.wifiArrayWriteIndex is not None
                else config.deviceStates.wfaIndex,
            )
        )
    if config.deviceSubStates is not None:
        _LOGGER.debug("Adding SUB_STATE EnumEntityDescription")
        result.append(
            EnumEntityDescription(
                "SUB_STATE",
                config.deviceSubStates.subStates,
                config.deviceSubStates.wifiArrayReadIndex,
                config.deviceStates.wifiArrayWriteIndex
                if config.deviceStates.wifiArrayWriteIndex
                else config.deviceStates.wfaIndex,
            )
        )
    result.append(ProgramEntityDescription(config.program))
    result.extend(generate_descriptions_from_features(config.subPrograms))

    # Remove redundant entities from device
    description_keys = [description.key for description in result]
    if "TEMPERATURE" in description_keys and "WASHER_TEMPERATURE" in description_keys:
        _LOGGER.debug("Removing redundant temperature description")
        del result[description_keys.index("WASHER_TEMPERATURE")]

    return result


class HomeWhizEntity(CoordinatorEntity[HomewhizCoordinator], SelectEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        description: HomeWhizEntitySelectDescription,
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
        self.byte_to_option = description.byte_to_option
        self.option_to_byte = description.option_to_byte
        self.read_index = description.read_index
        self.write_index = description.write_index
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
    def current_option(self) -> str | None:
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        return self.byte_to_option(clamp(self.coordinator.data[self.read_index]))

    async def async_select_option(self, option: str):
        value = self.option_to_byte(option)
        self.coordinator.send_command(self.write_index, value)

    @property
    def available(self) -> bool:
        return self.coordinator.is_connected

    @property
    def name(self) -> str | None:
        key = self.entity_description.key
        if key == "STATE":
            return "State"
        if key == "SUB_STATE":
            return "Sub-state"
        return self._localization.get(key, key)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = EntryData(
        contents=from_dict(ApplianceContents, entry.data["contents"]),
        appliance_info=from_dict(ApplianceInfo, entry.data["appliance_info"])
        if entry.data["appliance_info"] is not None
        else None,
        ids=from_dict(IdExchangeResponse, entry.data["ids"]),
        cloud_config=None,
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = generate_descriptions_from_config(data.contents.config)
    _LOGGER.debug(f"Selects: {[d.key for d in descriptions]}")
    async_add_entities(
        [
            HomeWhizEntity(coordinator, description, entry, data)
            for description in descriptions
        ]
    )
