from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .appliance_controls import (
    Control,
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

# The only NumericControl currently known to need a corrected unit/device
# class. Arcelik's CONFIGURATION endpoint reports this field with a "hw"
# unit label (see the matching factor fix in appliance_controls.py's
# extract_ac_control) which isn't a real HA unit, so we map it to kW here.
# Scoped to this single key on purpose - other NumericControl sensors keep
# their previous (no explicit unit/device_class) behavior.
INSTANT_CONSUMPTION_KEY = "air_conditioner_instant_consumption"
# The bogus unit label that marks the affected reports. A device sending the
# same key with a real unit is left alone, matching the factor fix.
INSTANT_CONSUMPTION_BOGUS_UNIT = "hw"

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
        elif (
            isinstance(control, NumericControl)
            and control.key == INSTANT_CONSUMPTION_KEY
            and control.bounds.unit == INSTANT_CONSUMPTION_BOGUS_UNIT
        ):
            self._attr_native_unit_of_measurement = "kW"
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
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
    """Integrates the instant-consumption power (kW) sensor over time into
    an accumulated kWh total, ready to be added to the HA Energy dashboard.

    The appliance itself does not report a running kWh total, only
    instantaneous power - this entity does a trapezoidal integration of
    that value every time the coordinator pushes new data, and persists
    the running total across HA restarts via RestoreEntity so it behaves
    like a proper "total_increasing" energy meter.

    Scoped with the exact same key+unit check as the kW sensor above, on
    purpose - only appliances confirmed to expose the buggy "hw"-labeled
    instant-consumption field get this companion entity.
    """

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
        # clobbering the class-level SensorDeviceClass.ENERGY. Re-assert it
        # here so HA recognizes this as a proper energy sensor (otherwise
        # the Energy dashboard rejects it with "Unexpected device class").
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._power_control = power_control
        self._total_kwh: float = 0.0
        self._last_update: datetime | None = None
        self._last_power_kw: float | None = None

    @staticmethod
    def parse_restored_total(state: str | None) -> float:
        """Pure helper: turn a restored HA state string back into a kWh
        total. Anything that isn't a plain finite number (missing state,
        "unknown", "unavailable", or garbage) resets to 0.0 rather than
        raising or silently carrying over a stale/invalid value."""
        if state is None or state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return 0.0
        try:
            value = float(state)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(value):
            return 0.0
        return value

    @staticmethod
    def integrate_delta(
        last_power_kw: float | None, power_kw: float, elapsed_hours: float
    ) -> float:
        """Pure helper: trapezoidal kWh delta for one step between two
        power (kW) samples elapsed_hours apart. Returns 0.0 (a no-op) when
        there's no previous sample yet, or when the gap is too large to
        trust the "constant power over the gap" assumption - e.g. HA was
        down or the appliance was offline for a while."""
        if last_power_kw is None:
            return 0.0
        if elapsed_hours <= 0 or elapsed_hours > MAX_INTEGRATION_GAP_HOURS:
            return 0.0
        avg_power_kw = (last_power_kw + power_kw) / 2
        return avg_power_kw * elapsed_hours

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        self._total_kwh = self.parse_restored_total(
            last_state.state if last_state is not None else None
        )
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

    def _advance_integration(self, now: datetime) -> None:
        """Pure state update: no HA runtime/event-loop needed, so this can
        be unit tested directly without a real hass instance."""
        power_kw = self._current_power_kw()

        if power_kw is not None:
            if self._last_update is not None:
                elapsed_hours = (now - self._last_update).total_seconds() / 3600
                self._total_kwh += self.integrate_delta(
                    self._last_power_kw, power_kw, elapsed_hours
                )
            self._last_power_kw = power_kw
            self._last_update = now

    def _handle_coordinator_update(self) -> None:
        self._advance_integration(datetime.now(UTC))
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:  # type: ignore[override]
        return round(self._total_kwh, 4)


def _find_instant_consumption_controls(
    sensor_controls: Sequence[Control],
) -> list[NumericControl]:
    """The exact same key+unit signature used by HomeWhizSensorEntity above
    to decide which sensor gets the kW/POWER/MEASUREMENT treatment - reused
    here so the companion kWh entity only ever appears for the same,
    verified-affected appliances."""
    return [
        c
        for c in sensor_controls
        if isinstance(c, NumericControl)
        and c.key == INSTANT_CONSUMPTION_KEY
        and c.bounds.unit == INSTANT_CONSUMPTION_BOGUS_UNIT
    ]


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

    homewhiz_sensor_entities.extend(
        HomeWhizEnergyEntity(coordinator, control, entry.title, data)
        for control in _find_instant_consumption_controls(sensor_controls)
    )

    _LOGGER.debug(
        "Entities: %s",
        {entity.entity_key: entity for entity in homewhiz_sensor_entities},
    )
    async_add_entities(homewhiz_sensor_entities)
