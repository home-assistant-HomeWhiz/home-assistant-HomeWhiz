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

from .appliance_controls import ClimateControl, generate_controls_from_config
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
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


class HomeWhizClimateEntity(HomeWhizEntity, ClimateEntity):
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: ClimateControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return list(program_dict.values()) + [HVACMode.OFF]

    @property
    def is_off(self):
        return self._control.state.get_value(self.coordinator.data)

    @property
    def hvac_mode_raw(self):
        option = self._control.program.get_value(self.coordinator.data)
        if option is None:
            return None
        return program_dict[option]

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
            await self.coordinator.send_command(self._control.state.set_value(False))
            return
        if self.is_off:
            await self.coordinator.send_command(self._control.state.set_value(True))
        if self.hvac_mode_raw != hvac_mode:
            program_key = program_dict.inverse.get(hvac_mode)
            await self.coordinator.send_command(
                self._control.program.set_value(program_key)
            )

    @property
    def target_temperature_step(self) -> float:
        return self._control.target_temperature.bounds.step

    @property
    def target_temperature_low(self) -> float:
        return self._control.target_temperature.bounds.lowerLimit

    @property
    def target_temperature_high(self) -> float:
        return self._control.target_temperature.bounds.upperLimit

    @property
    def target_temperature(self) -> float | None:
        if not self.available:
            return STATE_UNAVAILABLE
        if self.coordinator.data is None:
            return None
        return self._control.target_temperature.get_value(self.coordinator.data)

    async def async_set_temperature(self, temperature: float, **kwargs):
        _LOGGER.debug(f"Changing temperature {temperature}")
        await self.coordinator.send_command(
            self._control.target_temperature.set_value(temperature)
        )

    @property
    def current_temperature(self):
        return self._control.current_temperature.get_value(self.coordinator.data)

    @property
    def fan_modes(self):
        return list(wind_strength_dict.values())

    @property
    def fan_mode(self) -> str | None:
        option = self._control.fan_mode.get_value(self.coordinator.data)
        if option is None:
            return None
        return wind_strength_dict[option]

    async def async_set_fan_mode(self, fan_mode: str):
        _LOGGER.debug(f"Changing fan mode {fan_mode}")
        wind_strength_key = wind_strength_dict.inverse.get(fan_mode)
        await self.coordinator.send_command(
            self._control.fan_mode.set_value(wind_strength_key)
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(data.contents.config)
    climate_controls = [c for c in controls if isinstance(c, ClimateControl)]
    _LOGGER.debug(f"ACs: {[c.key for c in climate_controls]}")
    async_add_entities(
        [
            HomeWhizClimateEntity(coordinator, control, entry.title, data)
            for control in climate_controls
        ]
    )
