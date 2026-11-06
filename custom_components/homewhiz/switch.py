from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance_config import ApplianceState
from .appliance_controls import (
    BooleanCompareControl,
    WriteBooleanControl,
    WriteEnumControl,
    generate_controls_from_config,
    to_friendly_name,
)
from .config_flow import EntryData
from .const import DOMAIN
from .entity import HomeWhizEntity
from .helper import build_entry_data
from .homewhiz import HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

POWER_KEY = "device_power"
# The washer is left out: in a Daily log of the BLE-only washer the remote
# control was 0 while it was off and only became enabled after it was switched
# on at the appliance, and 34:10 without the release had no effect. The
# dishwasher (3) is not tested on a real device.
POWER_APPLIANCE_TYPES = {3, 5}
POWER_ON = "device_state_on"
POWER_OFF = "device_state_off"


def allowed_transitions(states: ApplianceState) -> dict[str, set[str]]:
    """Map each device state to the states it may change to, named as in the select."""
    return {
        to_friendly_name(option.strKey): {
            to_friendly_name(target) for target in (option.allowedTransitions or [])
        }
        for option in states.states
    }


def find_state_controls(
    entry_id: str, data: EntryData
) -> tuple[WriteEnumControl, BooleanCompareControl, ApplianceState] | None:
    """State, remote control and declared states of a supported appliance type."""
    info = data.appliance_info
    states = data.contents.config.deviceStates
    if (
        info is None
        or info.applianceType not in POWER_APPLIANCE_TYPES
        or states is None
    ):
        return None
    controls = generate_controls_from_config(entry_id, data.contents.config)
    state = next(
        (c for c in controls if c.key == "state" and isinstance(c, WriteEnumControl)),
        None,
    )
    remote = next(
        (
            c
            for c in controls
            if c.key == "remote_control" and isinstance(c, BooleanCompareControl)
        ),
        None,
    )
    if state is None or remote is None:
        return None
    return state, remote, states


class HomeWhizSwitchEntity(HomeWhizEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        control: WriteBooleanControl,
        device_name: str,
        data: EntryData,
    ):
        super().__init__(coordinator, device_name, control.key, data)
        self._control = control

    @property
    def is_on(self) -> bool | None:  # type: ignore[override]
        if self.coordinator.data is None:
            return None
        return self._control.get_value(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.send_command(self._control.set_value(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.send_command(self._control.set_value(False))


class PowerSwitch(HomeWhizEntity, SwitchEntity):
    """Switch the appliance on or off with the command of its state select."""

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        device_name: str,
        data: EntryData,
        state: WriteEnumControl,
        remote: BooleanCompareControl,
        states: ApplianceState,
    ) -> None:
        super().__init__(coordinator, device_name, POWER_KEY, data)
        # The base class uses a translation placeholder as its device class.
        self._attr_device_class = None
        self._state_control = state
        self._remote_control = remote
        self._allowed = allowed_transitions(states)

    def _current_state(self) -> str | None:
        packet = self.coordinator.data
        if packet is None or len(packet) <= self._state_control.read_index:
            return None
        return self._state_control.get_value(packet)

    @property
    def is_on(self) -> bool | None:  # type: ignore[override]
        state = self._current_state()
        return None if state is None else state != POWER_OFF

    @property
    def available(self) -> bool:
        """Require remote control and the one transition that flips the power."""
        packet = self.coordinator.data
        state = self._current_state()
        if not self.coordinator.is_connected or packet is None or state is None:
            return False
        if len(packet) <= self._remote_control.read_index:
            return False
        if not self._remote_control.get_value(packet):
            return False
        target = POWER_ON if state == POWER_OFF else POWER_OFF
        return target in self._allowed.get(state, set())

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._switch_to(POWER_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._switch_to(POWER_OFF)

    async def _switch_to(self, target: str) -> None:
        state = self._current_state()
        if state is not None and (state != POWER_OFF) == (target == POWER_ON):
            return
        if not self.available:
            raise HomeAssistantError(
                "This action is not available in the current device state"
            )
        await self.coordinator.send_command(self._state_control.set_value(target))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = build_entry_data(entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controls = generate_controls_from_config(entry.entry_id, data.contents.config)
    write_enum_controls = [c for c in controls if isinstance(c, WriteBooleanControl)]
    _LOGGER.debug("Switches: %s", [c.key for c in write_enum_controls])
    entities: list[SwitchEntity] = [
        HomeWhizSwitchEntity(coordinator, control, entry.title, data)
        for control in write_enum_controls
    ]
    found = find_state_controls(entry.entry_id, data)
    if found is not None:
        state, remote, states = found
        if POWER_ON in state.options.inverse and POWER_OFF in state.options.inverse:
            entities.append(
                PowerSwitch(coordinator, entry.title, data, state, remote, states)
            )
    async_add_entities(entities)
