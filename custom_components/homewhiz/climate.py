import logging

from dacite import from_dict
from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import ApplianceContents, ApplianceInfo, IdExchangeResponse
from .config_flow import EntryData
from .const import DOMAIN
from .homewhiz import HomewhizCoordinator, appliance_type_by_code, brand_name_by_code

_LOGGER: logging.Logger = logging.getLogger(__package__)

program_dict: dict[str, HVACMode] = {
    "AIR_CONDITIONER_MODE_COOLING": HVACMode.COOL,
    "AIR_CONDITIONER_MODE_AUTO": HVACMode.AUTO,
    "AIR_CONDITIONER_MODE_DRY": HVACMode.DRY,
    "AIR_CONDITIONER_MODE_HEATING": HVACMode.HEAT,
    "AIR_CONDITIONER_MODE_FAN": HVACMode.FAN_ONLY,
}

wind_strength_dict: dict[str, str] = {
    "WIND_STRENGTH_LOW": FAN_LOW,
    "WIND_STRENGTH_MID": FAN_MEDIUM,
    "WIND_STRENGTH_HIGH": FAN_HIGH,
    "WIND_STRENGTH_AUTO": FAN_AUTO,
}


def clamp(value: int):
    return value if value < 128 else value - 128


class HomeWhizClimateEntity(CoordinatorEntity[HomewhizCoordinator], ClimateEntity):
    _attr_has_entity_name = True
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        entry: ConfigEntry,
        data: EntryData,
    ):
        super().__init__(coordinator)
        unique_name = entry.title
        friendly_name = (
            data.appliance_info.name if data.appliance_info is not None else unique_name
        )

        self._localization = data.contents.localization
        self._attr_unique_id = f"{unique_name}_AC"
        manufacturer = (
            brand_name_by_code[data.appliance_info.brand]
            if data.appliance_info is not None
            else None
        )
        model = data.appliance_info.model if data.appliance_info is not None else None
        self._program = data.contents.config.program

        self._target_temperature_description = next(
            filter(
                lambda sub_program: sub_program.strKey
                == "AIR_CONDITIONER_TARGET_TEMPERATURE",
                data.contents.config.subPrograms,
            ),
            None,
        )
        self._wind_strength_description = next(
            filter(
                lambda sub_program: sub_program.strKey
                == "AIR_CONDITIONER_WIND_STRENGTH",
                data.contents.config.subPrograms,
            ),
            None,
        )

        self._device_states = data.contents.config.deviceStates
        self._state_on = next(
            filter(
                lambda state: state.strKey == "DEVICE_STATE_ON",
                self._device_states.states,
            )
        )
        self._state_off = next(
            filter(
                lambda state: state.strKey == "DEVICE_STATE_OFF",
                self._device_states.states,
            )
        )
        self._room_temperature_description = next(
            filter(
                lambda monitoring: monitoring.strKey
                == "AIR_CONDITIONER_ROOM_TEMPERATURE",
                data.contents.config.monitorings,
            ),
            None,
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_name)},
            name=friendly_name,
            manufacturer=manufacturer,
            model=model,
        )

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return list(program_dict.values()) + [HVACMode.OFF]

    @property
    def is_off(self):
        state_value = clamp(
            self.coordinator.data[self._device_states.wifiArrayReadIndex]
        )
        return state_value == self._state_off.wifiArrayValue

    @property
    def hvac_mode_raw(self):
        value = clamp(self.coordinator.data[self._program.wifiArrayIndex])
        for option in self._program.values:
            if option.wifiArrayValue == value:
                return program_dict[option.strKey]
        return None

    @property
    def hvac_mode(self) -> HVACMode | None:
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        if self.is_off:
            return HVACMode.OFF
        return self.hvac_mode_raw

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        _LOGGER.debug(f"Changing HVAC mode {hvac_mode}")
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.send_command(
                self._device_states.wifiArrayWriteIndex, self._state_off.wifiArrayValue
            )
            return
        if self.is_off:
            await self.coordinator.send_command(
                self._device_states.wifiArrayWriteIndex, self._state_on.wifiArrayValue
            )
        if self.hvac_mode_raw != hvac_mode:
            selected_state = next(
                filter(
                    lambda state: program_dict[state.strKey] == hvac_mode,
                    self._program.values,
                )
            )
            await self.coordinator.send_command(
                self._program.wifiArrayIndex, selected_state.wifiArrayValue
            )

    @property
    def target_temperature_step(self) -> float:
        return self._target_temperature_description.boundedValues[0].step

    @property
    def target_temperature_low(self) -> float:
        return self._target_temperature_description.boundedValues[0].lowerLimit

    @property
    def target_temperature_high(self) -> float:
        return self._target_temperature_description.boundedValues[0].upperLimit

    @property
    def target_temperature(self) -> float | None:
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        value = clamp(
            self.coordinator.data[self._target_temperature_description.wifiArrayIndex]
        )
        return value * self._target_temperature_description.boundedValues[0].factor

    async def async_set_temperature(self, temperature: float, **kwargs):
        _LOGGER.debug(f"Changing temperature {temperature}")
        await self.coordinator.send_command(
            self._target_temperature_description.wifiArrayIndex, int(temperature)
        )

    @property
    def current_temperature(self):
        value = clamp(
            self.coordinator.data[self._room_temperature_description.wifiArrayIndex]
        )
        return value * self._room_temperature_description.boundedValues[0].factor

    @property
    def fan_modes(self):
        return list(wind_strength_dict.values())

    @property
    def fan_mode(self) -> str | None:
        value = clamp(
            self.coordinator.data[self._wind_strength_description.wifiArrayIndex]
        )
        for option in self._wind_strength_description.enumValues:
            if option.wifiArrayValue == value:
                return wind_strength_dict[option.strKey]
        return None

    async def async_set_fan_mode(self, fan_mode: str):
        _LOGGER.debug(f"Changing fan mode {fan_mode}")
        selected_option = next(
            filter(
                lambda option: wind_strength_dict[option.strKey] == fan_mode,
                self._wind_strength_description.enumValues,
            )
        )
        await self.coordinator.send_command(
            self._wind_strength_description.wifiArrayIndex,
            selected_option.wifiArrayValue,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.is_connected


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
        data.appliance_info is None
        or not appliance_type_by_code[data.appliance_info.applianceType]
        == "AIR_CONDITIONER"
    ):
        return
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeWhizClimateEntity(coordinator, entry, data)])
