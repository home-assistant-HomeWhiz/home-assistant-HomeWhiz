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
    ApplianceFeatureEnumOption,
    ApplianceProgram,
)
from .config_flow import EntryData
from .const import DOMAIN
from .homewhiz import HomewhizCoordinator, appliance_type_by_code, brand_name_by_code

_LOGGER: logging.Logger = logging.getLogger(__package__)


def unit_for_key(key: str):
    if "TEMP" in key:
        return " " + TEMP_CELSIUS
    if "SPIN" in key:
        return " RPM"
    return ""


def clamp(value: int):
    return value if value < 128 else value - 128


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
        for option in self.enum_options:
            if option.wifiArrayValue == byte:
                return option.strKey
        return None

    def option_to_byte(self, value):
        for option in self.enum_options:
            if option.strKey == value:
                return option.wifiArrayValue
        return None


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


def generate_select_descriptions_from_features(features: list[ApplianceFeature]):
    result = []
    for feature in features:
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
                        options[wifiValue] = str(value) + unit_for_key(feature.strKey)
                    value += boundedValues.step
        result.append(
            EnumSelectEntityDescription(
                feature.strKey,
                [
                    ApplianceFeatureEnumOption(options[key], key)
                    for key in options.keys()
                ],
                read_index=feature.wifiArrayIndex,
                write_index=(
                    feature.wfaWriteIndex
                    if feature.wfaWriteIndex is not None
                    else feature.wifiArrayIndex
                ),
            )
        )
    return result


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
        friendly_name = (
            data.appliance_info.name if data.appliance_info is not None else unique_name
        )

        self._localization = data.contents.localization
        self.entity_description = description
        self.byte_to_option = description.byte_to_option
        self.option_to_byte = description.option_to_byte
        self.get_option = description.get_option
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
    data = EntryData(
        contents=from_dict(ApplianceContents, entry.data["contents"]),
        appliance_info=from_dict(ApplianceInfo, entry.data["appliance_info"])
        if entry.data["appliance_info"] is not None
        else None,
        ids=from_dict(IdExchangeResponse, entry.data["ids"]),
        cloud_config=None,
    )
    if (
        data.appliance_info is not None
        and appliance_type_by_code[data.appliance_info.applianceType]
        == "AIR_CONDITIONER"
    ):
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
