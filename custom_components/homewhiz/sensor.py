from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .appliance_controls import (
    DebugControl,
    EnumControl,
    NumericControl,
    StateAwareRemainingTimeControl,
    SummedTimestampControl,
    TimeControl,
    generate_controls_from_config,
)
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

# If the coordinator hasn't pushed an update for longer than this, we don't
# trust the "constant power over the gap" assumption (e.g. HA was down, or
# the appliance dropped offline) - skip integrating that particular gap
# instead of risking a bogus energy spike/dip on the Energy dashboard.
MAX_INTEGRATION_GAP_HOURS = 1.0


class HomeWhizSensorEntity(HomeWhizEntity, SensorEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: TimeControl
        | EnumControl
        | NumericControl
        | DebugControl
        | SummedTimestampControl
        | StateAwareRemainingTimeControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control
        if isinstance(control, (TimeControl, StateAwareRemainingTimeControl)):
            self._attr_icon = "mdi:clock-outline"
            self._attr_native_unit_of_measurement = "min"
            self._attr_device_class = SensorDeviceClass.DURATION
        elif isinstance(control, EnumControl):
            self._attr_device_class = SensorDeviceClass.ENUM  # type:ignore
            self._attr_options = list(self._control.options.values())  # type:ignore
        elif isinstance(control, NumericControl):
            unit = control.bounds.unit
            # Arcelik reports this consumption field with an unusable "hw"
            # unit label; the value itself is corrected to real kW via the
            # factor override in appliance_controls.py, so show it as kW.
            if unit == "hw":
                unit = "kW"
                self._attr_device_class = SensorDeviceClass.POWER
                self._attr_state_class = SensorStateClass.MEASUREMENT
            elif unit == "°C":
                self._attr_device_class = SensorDeviceClass.TEMPERATURE
            if unit:
                self._attr_native_unit_of_measurement = unit
        elif isinstance(control, SummedTimestampControl):
            self._attr_icon = "mdi:camera-timer"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:  # type: ignore[override]
        """Attribute to identify the origin of the data used"""
        if isinstance(self._control, SummedTimestampControl):
            return {
                "sources": [
                    x.my_entity_ids
                    for x in self._control.sensors
                    if hasattr(x, "my_entity_ids")
                ]
            }
        return None

    @property
    def native_value(  # type: ignore[override]
        self,
    ) -> float | int | str | datetime | None:
        _LOGGER.debug(
            "Native value for entity %s, id: %s, info: %s, class:%s, is %s",
            self.entity_key,
            self._attr_unique_id,
            self._attr_device_info,
            self._attr_device_class,
            self.coordinator.data,
        )

        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)


class HomeWhizEnergyEntity(HomeWhizEntity, SensorEntity, RestoreEntity):
    """Integrates an instantaneous power (kW) NumericControl over time into
    an accumulated kWh total, ready to be added to the HA Energy dashboard.

    The appliance itself does not report a running kWh total, only
    instantaneous power - this entity does a trapezoidal integration of
    that value every time the coordinator pushes new data, and persists
    the running total across HA restarts via RestoreEntity so it behaves
    like a proper "total_increasing" energy meter.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        power_control: NumericControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, f"{power_control.key}_total", data)
        # HomeWhizEntity.__init__ (called just above) unconditionally sets
        # self._attr_device_class to a homewhiz-internal placeholder value,
        # clobbering the SensorDeviceClass.ENERGY class attribute defined
        # above. Re-assert it here so HA recognizes this as a proper energy
        # sensor (otherwise the Energy dashboard rejects it with
        # "Unexpected device class").
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._power_control = power_control
        self._total_kwh: float = 0.0
        self._last_update: datetime | None = None
        self._last_power_kw: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            None,
            "unknown",
            "unavailable",
        ):
            try:
                self._total_kwh = float(last_state.state)
            except (TypeError, ValueError):
                self._total_kwh = 0.0
        # Prime the integration baseline now, so the very first coordinator
        # update after startup doesn't integrate over the (possibly huge)
        # gap since HA was last running.
        self._last_update = datetime.now(UTC)
        current = self._current_power_kw()
        if current is not None:
            self._last_power_kw = current

    def _current_power_kw(self) -> float | None:
        if self.coordinator.data is None:
            return None
        value = self._power_control.get_value(self.coordinator.data)
        return float(value) if value is not None else None

    def _handle_coordinator_update(self) -> None:
        now = datetime.now(UTC)
        power_kw = self._current_power_kw()

        if power_kw is not None:
            if self._last_update is not None and self._last_power_kw is not None:
                elapsed_hours = (now - self._last_update).total_seconds() / 3600
                if 0 < elapsed_hours <= MAX_INTEGRATION_GAP_HOURS:
                    avg_power_kw = (self._last_power_kw + power_kw) / 2
                    self._total_kwh += avg_power_kw * elapsed_hours
            self._last_power_kw = power_kw
            self._last_update = now

        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:  # type: ignore[override]
        return round(self._total_kwh, 4)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(entry.entry_id, data.contents.config)
    _LOGGER.debug("Generated controls: %s", controls)
    sensor_controls = [
        c
        for c in controls
        if isinstance(
            c,
            (
                TimeControl,
                EnumControl,
                NumericControl,
                DebugControl,
                SummedTimestampControl,
                StateAwareRemainingTimeControl,
            ),
        )
    ]

    _LOGGER.debug("Sensors: %s", [c.key for c in sensor_controls])

    homewhiz_sensor_entities: list[HomeWhizSensorEntity | HomeWhizEnergyEntity] = [
        HomeWhizSensorEntity(coordinator, control, entry.title, data)
        for control in sensor_controls
    ]

    # For every instantaneous power ("hw" -> kW) control, also add a
    # companion kWh accumulator entity for the Energy dashboard.
    power_controls = [
        c
        for c in sensor_controls
        if isinstance(c, NumericControl) and c.bounds.unit == "hw"
    ]
    homewhiz_sensor_entities.extend(
        HomeWhizEnergyEntity(coordinator, control, entry.title, data)
        for control in power_controls
    )

    _LOGGER.debug(
        "Entities: %s",
        {entity.entity_key: entity for entity in homewhiz_sensor_entities},
    )
    async_add_entities(homewhiz_sensor_entities)
