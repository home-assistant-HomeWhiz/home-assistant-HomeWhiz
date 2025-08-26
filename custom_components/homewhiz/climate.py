import logging
from typing import Any

from homeassistant.components.climate import (  # type: ignore[import]
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance_controls import ClimateControl, generate_controls_from_config
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class HomeWhizClimateEntity(HomeWhizEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    # https://developers.home-assistant.io/blog/2024/01/24/climate-climateentityfeatures-expanded/
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: ClimateControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control
        self._previous_hvac_mode: HVACMode | None = None

    @property
    def supported_features(self) -> ClimateEntityFeature:  # type: ignore[override]
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )
        if self._control.swing.enabled:
            features |= ClimateEntityFeature.SWING_MODE
        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:  # type: ignore[override]
        return self._control.hvac_mode.options

    @property
    def hvac_mode(self) -> HVACMode | None:  # type: ignore[override]
        data = self.coordinator.data
        if data is None:
            return None
        return self._control.hvac_mode.get_value(data)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        _LOGGER.debug("Changing HVAC mode %s", hvac_mode)
        data = self.coordinator.data
        if data is None:
            return
        commands = self._control.hvac_mode.set_value(hvac_mode, data)
        for command in commands:
            await self.coordinator.send_command(command)

    async def async_turn_off(self) -> None:
        self._previous_hvac_mode = self.hvac_mode
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(
            self._previous_hvac_mode if self._previous_hvac_mode else HVACMode.HEAT_COOL
        )

    @property
    def target_temperature_step(self) -> float:  # type: ignore[override]
        return self._control.target_temperature.bounds.step

    @property
    def target_temperature_low(self) -> float:  # type: ignore[override]
        return self._control.target_temperature.bounds.lowerLimit

    @property
    def target_temperature_high(self) -> float:  # type: ignore[override]
        return self._control.target_temperature.bounds.upperLimit

    @property
    def target_temperature(self) -> float | None:  # type: ignore[override]
        if self.coordinator.data is None:
            return None
        return self._control.target_temperature.get_value(self.coordinator.data)

    async def async_set_temperature(self, temperature: float, **kwargs: Any) -> None:  # type: ignore[override]
        _LOGGER.debug("Changing temperature %s", temperature)
        await self.coordinator.send_command(
            self._control.target_temperature.set_value(temperature)
        )

    @property
    def current_temperature(self) -> float | None:  # type: ignore[override]
        return self._control.current_temperature.get_value(self.coordinator.data)

    @property
    def fan_modes(self) -> list[str]:  # type: ignore[override]
        return list(self._control.fan_mode.options.values())

    @property
    def fan_mode(self) -> str | None:  # type: ignore[override]
        return self._control.fan_mode.get_value(self.coordinator.data)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        _LOGGER.debug("Changing fan mode %s", fan_mode)
        await self.coordinator.send_command(self._control.fan_mode.set_value(fan_mode))

    @property
    def swing_modes(self) -> list[str] | None:  # type: ignore[override]
        return self._control.swing.options

    @property
    def swing_mode(self) -> str | None:  # type: ignore[override]
        if self.coordinator.data is None:
            return None
        return self._control.swing.get_value(self.coordinator.data)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        _LOGGER.debug("Changing swing mode %s", swing_mode)
        if self.coordinator.data is None:
            return
        commands = self._control.swing.set_value(swing_mode, self.coordinator.data)
        for command in commands:
            await self.coordinator.send_command(command)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(entry.entry_id, data.contents.config)
    climate_controls = [c for c in controls if isinstance(c, ClimateControl)]
    _LOGGER.debug("ACs: %s", [c.key for c in climate_controls])
    async_add_entities(
        [
            HomeWhizClimateEntity(coordinator, control, entry.title, data)
            for control in climate_controls
        ]
    )
