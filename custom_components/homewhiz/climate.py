import logging

from bidict import bidict
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import EntryData
from .const import DOMAIN
from .helper import (
    build_device_info,
    build_entry_data,
    clamp,
    find_by_key,
    find_by_value,
    is_air_conditioner,
)
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

program_dict: bidict[str, HVACMode] = bidict(
    {
        "AIR_CONDITIONER_MODE_COOLING": HVACMode.COOL,
        "AIR_CONDITIONER_MODE_AUTO": HVACMode.AUTO,
        "AIR_CONDITIONER_MODE_DRY": HVACMode.DRY,
        "AIR_CONDITIONER_MODE_HEATING": HVACMode.HEAT,
        "AIR_CONDITIONER_MODE_FAN": HVACMode.FAN_ONLY,
    }
)

wind_strength_dict: bidict[str, str] = bidict(
    {
        "WIND_STRENGTH_LOW": FAN_LOW,
        "WIND_STRENGTH_MID": FAN_MEDIUM,
        "WIND_STRENGTH_HIGH": FAN_HIGH,
        "WIND_STRENGTH_AUTO": FAN_AUTO,
    }
)


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

        self._localization = data.contents.localization
        self._attr_unique_id = f"{unique_name}_AC"
        self._attr_device_info = build_device_info(unique_name, data)

        self._program = data.contents.config.program

        self._target_temperature_description = find_by_key(
            "AIR_CONDITIONER_TARGET_TEMPERATURE", data.contents.config.subPrograms
        )
        self._wind_strength_description = find_by_key(
            "AIR_CONDITIONER_WIND_STRENGTH", data.contents.config.subPrograms
        )
        self._device_states = data.contents.config.deviceStates
        self._state_on = find_by_key("DEVICE_STATE_ON", self._device_states.states)
        self._state_off = find_by_key("DEVICE_STATE_OFF", self._device_states.states)
        self._room_temperature_description = find_by_key(
            "AIR_CONDITIONER_ROOM_TEMPERATURE",
            data.contents.config.monitorings,
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
        option = find_by_value(value, self._program.values)
        if option is None:
            return None
        return program_dict[option.strKey]

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
        program_key = program_dict.inverse.get(hvac_mode)
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
            selected_program = find_by_key(program_key, self._program.values)
            if selected_program is None:
                raise f"No program found for fan mode {hvac_mode} in {self._program}"
            await self.coordinator.send_command(
                self._program.wifiArrayIndex, selected_program.wifiArrayValue
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
        option = find_by_value(value, self._wind_strength_description.enumValues)
        if option is None:
            return None
        return wind_strength_dict[option.strKey]

    async def async_set_fan_mode(self, fan_mode: str):
        _LOGGER.debug(f"Changing fan mode {fan_mode}")
        wind_strength_key = wind_strength_dict.inverse.get(fan_mode)
        selected_option = find_by_key(
            wind_strength_key, self._wind_strength_description.enumValues
        )
        if selected_option is None:
            raise (
                f"No option found for fan mode {fan_mode} "
                f"in {self._wind_strength_description}"
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
    data = build_entry_data(entry)
    if not is_air_conditioner(data):
        _LOGGER.debug("Appliance is not AC, not adding Climate entity")
        return
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeWhizClimateEntity(coordinator, entry, data)])
