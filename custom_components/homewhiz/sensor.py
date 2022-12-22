from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Callable

from dacite import from_dict
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
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
    ApplianceProgressFeature,
)
from .config_flow import EntryData
from .const import DOMAIN
from .homewhiz import HomewhizCoordinator, appliance_type_by_code, brand_name_by_code

_LOGGER: logging.Logger = logging.getLogger(__package__)


def clamp(value: int):
    return value if value < 128 else value - 128


@dataclass
class HomeWhizSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[bytearray], float | str | None] | None = None


class EnumSensorEntityDescription(HomeWhizSensorEntityDescription):
    def __init__(
        self, key: str, options: list[ApplianceFeatureEnumOption], read_index: int
    ):
        self.key = key
        self.icon = "mdi:state-machine"
        self.enum_options = options
        self.options = [option.strKey for option in options]
        self._read_index = read_index
        self.device_class = f"{DOMAIN}__{self.key}"

    def value_fn(self, data):
        value = clamp(data[self._read_index])
        for option in self.enum_options:
            if option.wifiArrayValue == value:
                return option.strKey
        return None


class SubProgramBoundedSensorEntityDescription(HomeWhizSensorEntityDescription):
    def __init__(
        self, parent_key: str, bounds: ApplianceFeatureBoundedOption, read_index: int
    ):
        self.key = bounds.strKey if bounds.strKey else parent_key
        self._bounds = bounds
        self._read_index = read_index

    def value_fn(self, data):
        return clamp(data[self._read_index]) * self._bounds.factor

    @property
    def native_unit_of_measurement(self):
        if "TEMP" in self.key:
            return TEMP_CELSIUS
        if "SPIN" in self.key:
            return "RPM"

    @property
    def icon(self):
        if "TEMP" in self.key:
            return "mdi:thermometer"
        if "SPIN" in self.key:
            return "mdi:rotate-3d-variant"


class ProgressSensorEntityDescription(HomeWhizSensorEntityDescription):
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


def generate_sensor_descriptions_from_features(features: list[ApplianceFeature]):
    result = []
    for feature in features:
        read_index = feature.wifiArrayIndex
        if feature.boundedValues is not None:
            for bounds in feature.boundedValues:
                result.append(
                    SubProgramBoundedSensorEntityDescription(
                        feature.strKey, bounds, read_index
                    )
                )
    return result


def generate_sensor_descriptions_from_config(
    config: ApplianceConfiguration,
) -> list[HomeWhizSensorEntityDescription]:
    _LOGGER.debug("Generating descriptions from config")
    result = []
    if config.deviceSubStates is not None:
        _LOGGER.debug("Adding SUB_STATE EnumEntityDescription")
        result.append(
            EnumSensorEntityDescription(
                "SUB_STATE",
                config.deviceSubStates.subStates,
                config.deviceSubStates.wifiArrayReadIndex,
            )
        )
    result.extend(generate_sensor_descriptions_from_features(config.subPrograms))
    if config.progressVariables is not None:
        _LOGGER.debug("Adding config progress variables")
        for field in fields(config.progressVariables):
            feature = getattr(config.progressVariables, field.name)
            if feature is not None:
                result.append(
                    ProgressSensorEntityDescription(feature),
                )
    if config.monitorings is not None:
        _LOGGER.debug("Adding config monitorings")
        result.extend(generate_sensor_descriptions_from_features(config.monitorings))

    return result


class HomeWhizSensorEntity(CoordinatorEntity[HomewhizCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        description: HomeWhizSensorEntityDescription,
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
    descriptions = generate_sensor_descriptions_from_config(data.contents.config)
    _LOGGER.debug(f"Sensors: {[d.key for d in descriptions]}")
    async_add_entities(
        [
            HomeWhizSensorEntity(coordinator, description, entry, data)
            for description in descriptions
        ]
    )
