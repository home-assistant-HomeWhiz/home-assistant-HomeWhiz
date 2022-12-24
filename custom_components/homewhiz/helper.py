from __future__ import annotations

from typing import TypeVar

from dacite import from_dict
from homeassistant.core import DOMAIN
from homeassistant.helpers.entity import DeviceInfo

from custom_components.homewhiz import IdExchangeResponse
from custom_components.homewhiz.api import ApplianceContents, ApplianceInfo
from custom_components.homewhiz.appliance_config import (
    ApplianceFeature,
    ApplianceFeatureBoundedOption,
    ApplianceFeatureEnumOption,
    ApplianceFeatureNotificationInfo,
    ApplianceProgram,
    ApplianceProgramDownloadSettings,
    ApplianceProgressFeature,
    ApplianceRemoteControl,
    ApplianceWarningOption,
    OvenMeatProbePlug,
)
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.homewhiz import (
    appliance_type_by_code,
    brand_name_by_code,
)

WithKey = TypeVar(
    "WithKey",
    ApplianceFeatureEnumOption,
    ApplianceProgram,
    ApplianceFeatureBoundedOption,
    ApplianceFeature,
    ApplianceProgressFeature,
    ApplianceFeatureNotificationInfo,
    ApplianceProgramDownloadSettings,
    ApplianceWarningOption,
)


def find_by_key(key: str, elements: list[WithKey]) -> WithKey | None:
    return next(
        filter(
            lambda element: element.strKey == key,
            elements,
        ),
        None,
    )


WithValue = TypeVar(
    "WithValue", ApplianceFeatureEnumOption, OvenMeatProbePlug, ApplianceRemoteControl
)


def find_by_value(value: int, elements: list[WithValue]) -> WithValue | None:
    return next(
        filter(
            lambda element: element.wifiArrayValue == value,
            elements,
        ),
        None,
    )


def build_entry_data(entry):
    return EntryData(
        contents=from_dict(ApplianceContents, entry.data["contents"]),
        appliance_info=from_dict(ApplianceInfo, entry.data["appliance_info"])
        if entry.data["appliance_info"] is not None
        else None,
        ids=from_dict(IdExchangeResponse, entry.data["ids"]),
        cloud_config=None,
    )


def clamp(value: int):
    return value if value < 128 else value - 128


def is_air_conditioner(data: EntryData):
    return (
        data.appliance_info is not None
        and appliance_type_by_code[data.appliance_info.applianceType]
        == "AIR_CONDITIONER"
    )


def build_device_info(unique_name: str, data: EntryData):
    friendly_name = (
        data.appliance_info.name if data.appliance_info is not None else unique_name
    )
    manufacturer = (
        brand_name_by_code[data.appliance_info.brand]
        if data.appliance_info is not None
        else None
    )
    model = data.appliance_info.model if data.appliance_info is not None else None
    return DeviceInfo(
        identifiers={(DOMAIN, unique_name)},
        name=friendly_name,
        manufacturer=manufacturer,
        model=model,
    )
