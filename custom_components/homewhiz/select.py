from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .appliance_config import (
    ApplianceConfiguration,
    ApplianceFeature,
    ApplianceFeatureEnumOption,
    ApplianceProgram,
)
from .config_flow import EntryData
from .const import DOMAIN
from .helper import (
    build_device_info,
    build_entry_data,
    clamp,
    find_by_key,
    find_by_value,
    is_air_conditioner,
    unit_for_key,
)
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass
class HomeWhizSelectEntityDescription(SelectEntityDescription):
    read_index: int | None = None
    write_index: int | None = None

    byte_to_option: Callable[[int], float | str | None] | None = None
    option_to_byte: Callable[[str], int] | None = None

    def get_option(self, data: bytearray):
        return self.byte_to_option(clamp(data[self.read_index]))


class EnumSelectEntityDescription(HomeWhizSelectEntityDescription):
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
        self.device_class = f"{DOMAIN}__{self.key}"

    def byte_to_option(self, byte):
        option = find_by_value(byte, self.enum_options)
        return option.strKey

    def option_to_byte(self, value):
        option = find_by_key(value, self.enum_options)
        return option.wifiArrayValue


class ProgramSelectEntityDescription(EnumSelectEntityDescription):
    def __init__(self, program: ApplianceProgram):
        super().__init__(
            program.strKey,
            program.values,
            program.wifiArrayIndex,
            program.wfaWriteIndex
            if program.wfaWriteIndex is not None
            else program.wifiArrayIndex,
        )


def generate_options_from_feature(feature: ApplianceFeature):
    options: dict[int, str] = {}
    if feature.enumValues is not None:
        options = options | {
            option.wifiArrayValue: option.strKey for option in feature.enumValues
        }
    if feature.boundedValues is not None:
        for boundedValues in feature.boundedValues:
            value = boundedValues.lowerLimit
            while value <= boundedValues.upperLimit:
                wifiValue = int(value / boundedValues.factor)
                if wifiValue not in options:
                    unit = unit_for_key(feature.strKey)
                    name = f"{value} {unit}" if unit is not None else str(value)
                    options[wifiValue] = name
                value += boundedValues.step
    return [
        ApplianceFeatureEnumOption(strKey=options[key], wifiArrayValue=key)
        for key in options.keys()
    ]


def generate_select_descriptions_from_features(features: list[ApplianceFeature]):
    return [
        EnumSelectEntityDescription(
            feature.strKey,
            generate_options_from_feature(feature),
            read_index=feature.wifiArrayIndex,
            write_index=(
                feature.wfaWriteIndex
                if feature.wfaWriteIndex is not None
                else feature.wifiArrayIndex
            ),
        )
        for feature in features
    ]


def generate_select_descriptions_from_config(
    config: ApplianceConfiguration,
) -> list[HomeWhizSelectEntityDescription]:
    _LOGGER.debug("Generating descriptions from config")
    result = []
    if config.deviceStates is not None:
        _LOGGER.debug("Adding STATE EnumEntityDescription")
        result.append(
            EnumSelectEntityDescription(
                "STATE",
                config.deviceStates.states,
                config.deviceStates.wifiArrayReadIndex,
                config.deviceStates.wifiArrayWriteIndex
                if config.deviceStates.wifiArrayWriteIndex is not None
                else config.deviceStates.wfaIndex,
            )
        )
    result.append(ProgramSelectEntityDescription(config.program))
    result.extend(generate_select_descriptions_from_features(config.subPrograms))

    return result


class HomeWhizSelectEntity(CoordinatorEntity[HomewhizCoordinator], SelectEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        description: HomeWhizSelectEntityDescription,
        entry: ConfigEntry,
        data: EntryData,
    ):
        super().__init__(coordinator)
        unique_name = entry.title
        self._attr_unique_id = f"{unique_name}_{description.key}"
        self._attr_device_info = build_device_info(unique_name, data)

        self._localization = data.contents.localization
        self.entity_description = description
        self.byte_to_option = description.byte_to_option
        self.option_to_byte = description.option_to_byte
        self.get_option = description.get_option
        self.write_index = description.write_index

    @property
    def current_option(self) -> str | None:
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        return self.get_option(self.coordinator.data)

    async def async_select_option(self, option: str):
        value = self.option_to_byte(option)
        await self.coordinator.send_command(self.write_index, value)

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
    data = build_entry_data(entry)
    if is_air_conditioner(data):
        _LOGGER.debug("Appliance is AC, not adding Select entities")
        return
    coordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = generate_select_descriptions_from_config(data.contents.config)
    _LOGGER.debug(f"Selects: {[d.key for d in descriptions]}")
    async_add_entities(
        [
            HomeWhizSelectEntity(coordinator, description, entry, data)
            for description in descriptions
        ]
    )
