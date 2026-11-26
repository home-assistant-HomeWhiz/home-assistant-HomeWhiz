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

# AUTO mode support for Arcelik ADE 607-2 cooker hood.
HOOD_AUTO_MODEL = "7704331217"
HOOD_AUTO_APPLIANCE_TYPE = 8
HOOD_AUTO_INDEX = 44
HOOD_AUTO_KEY = "hood_auto_mode"


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


class HoodAutoSwitchEntity(HomeWhizSwitchEntity):
    """Control AUTO mode on the supported cooker hood."""

    _attr_icon = "mdi:fan-auto"


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
