"""Tests for the native power switch.

Hass-free like the other platform tests: real controls from the fixtures, mock
coordinators, and the Bluetooth test drives the real coordinator method down to
the bytes written to the device.
"""

import asyncio
import dataclasses
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from dacite import from_dict
from homeassistant.exceptions import HomeAssistantError

from custom_components.homewhiz.api import (
    ApplianceContents,
    ApplianceInfo,
    IdExchangeResponse,
)
from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.appliance_controls import (
    BooleanCompareControl,
    WriteEnumControl,
    forget_controls,
    generate_controls_from_config,
)
from custom_components.homewhiz.bluetooth import HomewhizBluetoothUpdateCoordinator
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.const import DOMAIN
from custom_components.homewhiz.switch import (
    POWER_KEY,
    HomeWhizSwitchEntity,
    PowerSwitch,
    async_setup_entry,
    find_state_controls,
)

FIXTURES = Path(__file__).parent / "fixtures"
INTEGRATION = Path(__file__).parent.parent

# Real diagnostics: Bauknecht dryer applianceType 5. The dishwasher fixture has
# applianceType 3 only from the type table of the integration, no real
# dishwasher diagnostics or device test exist.
DRYER = ("bauknecht-dryer.json", "7188239270")
DISHWASHER = ("arcelik-dishwasher.json", "dishwasher-test")
DEVICES = [DRYER, DISHWASHER]
APPLIANCE_TYPE = {DRYER[1]: 5, DISHWASHER[1]: 3}


def _config(fixture: str) -> ApplianceConfiguration:
    return from_dict(
        ApplianceConfiguration, json.loads((FIXTURES / fixture).read_text())
    )


def _info(model: str, appliance_type: int = 1) -> ApplianceInfo:
    return ApplianceInfo(
        id=1,
        applianceId="appliance",
        brand=1,
        model=model,
        applianceType=appliance_type,
        platformType="platform",
        applianceSerialNumber=None,
        name="Test appliance",
        hsmId=None,
    )


def _entry_data(fixture: str, model: str, appliance_type: int = 1) -> EntryData:
    return EntryData(
        ids=IdExchangeResponse(appId="app"),
        contents=ApplianceContents(config=_config(fixture), localization={}),
        appliance_info=_info(model, appliance_type),
        cloud_config=None,
    )


def _controls(data: EntryData) -> tuple[WriteEnumControl, BooleanCompareControl]:
    # The control cache is keyed by entry id and survives between tests, so a
    # key reused for another fixture would silently return the wrong controls.
    forget_controls("test_power")
    controls = generate_controls_from_config("test_power", data.contents.config)
    state = next(c for c in controls if c.key == "state")
    remote = next(c for c in controls if c.key == "remote_control")
    assert isinstance(state, WriteEnumControl)
    assert isinstance(remote, BooleanCompareControl)
    return state, remote


def _packet(data: EntryData, state_name: str, remote_on: bool = True) -> bytearray:
    state, remote = _controls(data)
    packet = bytearray(120)
    packet[state.read_index] = state.options.inverse[state_name]
    packet[remote.read_index] = remote.compare_value if remote_on else 0
    return packet


def _coordinator(packet: bytearray | None, connected: bool = True) -> Mock:
    coordinator = Mock()
    coordinator.data = packet
    coordinator.is_connected = connected
    coordinator.send_command = AsyncMock()
    return coordinator


class _FakeClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.writes: list[tuple[str, bytearray]] = []

    async def write_gatt_char(self, characteristic: str, payload: bytearray) -> None:
        self.writes.append((characteristic, payload))


def _power_switch(coordinator: Any, data: EntryData) -> PowerSwitch:
    forget_controls("test_power")
    found = find_state_controls("test_power", data)
    assert found is not None
    state, remote, states = found
    return PowerSwitch(coordinator, "Test", data, state, remote, states)


@pytest.mark.parametrize(("fixture", "model"), DEVICES)
def test_supported_models_get_a_power_switch(fixture: str, model: str) -> None:
    data = _entry_data(fixture, model, appliance_type=APPLIANCE_TYPE[model])
    switch = _power_switch(_coordinator(None), data)

    assert switch.translation_key == POWER_KEY
    assert switch.unique_id == f"Test_{POWER_KEY}"
    # HomeWhizEntity sets a placeholder device class that is not valid here
    assert switch.device_class is None


@pytest.mark.parametrize(("fixture", "model"), DEVICES)
def test_is_on_everywhere_except_the_off_state(fixture: str, model: str) -> None:
    data = _entry_data(fixture, model, appliance_type=APPLIANCE_TYPE[model])
    state, _ = _controls(data)
    coordinator = _coordinator(None)
    switch = _power_switch(coordinator, data)

    assert switch.is_on is None
    for state_name in state.options.values():
        coordinator.data = _packet(data, state_name)
        assert switch.is_on is (state_name != "device_state_off"), state_name


@pytest.mark.parametrize(("fixture", "model"), DEVICES)
def test_available_in_every_state_with_the_remote_control(
    fixture: str, model: str
) -> None:
    """Every state of both appliances has exactly one way to flip the power."""
    data = _entry_data(fixture, model, appliance_type=APPLIANCE_TYPE[model])
    state, _ = _controls(data)
    coordinator = _coordinator(None)
    switch = _power_switch(coordinator, data)

    for state_name in state.options.values():
        coordinator.data = _packet(data, state_name)
        assert switch.available, state_name
        coordinator.data = _packet(data, state_name, remote_on=False)
        assert not switch.available, state_name


def test_not_available_without_a_usable_connection() -> None:
    data = _entry_data(*DRYER, appliance_type=5)
    coordinator = _coordinator(_packet(data, "device_state_running"))
    switch = _power_switch(coordinator, data)
    assert switch.available

    coordinator.is_connected = False
    assert not switch.available

    coordinator.is_connected = True
    coordinator.data = None
    assert not switch.available
    assert switch.is_on is None

    coordinator.data = bytearray(10)  # shorter than the state and remote indices
    assert not switch.available
    assert switch.is_on is None


@pytest.mark.parametrize(("fixture", "model"), DEVICES)
def test_turning_on_and_off_sends_the_command_of_the_state_select(
    fixture: str, model: str
) -> None:
    data = _entry_data(fixture, model, appliance_type=APPLIANCE_TYPE[model])
    state, _ = _controls(data)
    coordinator = _coordinator(_packet(data, "device_state_off"))
    switch = _power_switch(coordinator, data)

    asyncio.run(switch.async_turn_on())
    coordinator.send_command.assert_awaited_once_with(
        state.set_value("device_state_on")
    )

    coordinator.send_command.reset_mock()
    coordinator.data = _packet(data, "device_state_running")
    asyncio.run(switch.async_turn_off())
    coordinator.send_command.assert_awaited_once_with(
        state.set_value("device_state_off")
    )


@pytest.mark.parametrize(
    ("current", "turn_on"),
    [
        ("device_state_off", False),
        ("device_state_on", True),
        ("device_state_running", True),
        ("device_state_paused", True),
    ],
)
def test_switching_to_the_state_it_is_in_sends_nothing(
    current: str, turn_on: bool
) -> None:
    data = _entry_data(*DRYER, appliance_type=5)
    coordinator = _coordinator(_packet(data, current))
    switch = _power_switch(coordinator, data)

    asyncio.run(switch.async_turn_on() if turn_on else switch.async_turn_off())

    coordinator.send_command.assert_not_awaited()


def test_turning_on_while_it_runs_does_not_stop_the_appliance() -> None:
    """The dryer may go from running to on, the switch must not do that."""
    data = _entry_data(*DRYER, appliance_type=5)
    coordinator = _coordinator(_packet(data, "device_state_running"))
    switch = _power_switch(coordinator, data)

    asyncio.run(switch.async_turn_on())

    coordinator.send_command.assert_not_awaited()


def test_switching_rechecks_availability_and_sends_nothing() -> None:
    data = _entry_data(*DRYER, appliance_type=5)
    coordinator = _coordinator(_packet(data, "device_state_off", remote_on=False))
    switch = _power_switch(coordinator, data)

    with pytest.raises(HomeAssistantError):
        asyncio.run(switch.async_turn_on())
    coordinator.data = _packet(data, "device_state_running", remote_on=False)
    with pytest.raises(HomeAssistantError):
        asyncio.run(switch.async_turn_off())
    coordinator.data = None
    with pytest.raises(HomeAssistantError):
        asyncio.run(switch.async_turn_off())

    coordinator.send_command.assert_not_awaited()


@pytest.mark.parametrize(
    ("from_state", "turn_on", "last_byte"),
    [("device_state_off", True, 10), ("device_state_running", False, 20)],
)
def test_bluetooth_writes_the_same_bytes_as_the_select(
    from_state: str, turn_on: bool, last_byte: int
) -> None:
    data = _entry_data(*DRYER, appliance_type=5)
    state, _ = _controls(data)
    coordinator = object.__new__(HomewhizBluetoothUpdateCoordinator)
    client = _FakeClient()
    coordinator._connection = client  # type: ignore[assignment]
    coordinator._connection_lock = asyncio.Lock()
    coordinator.data = _packet(data, from_state)
    switch = _power_switch(coordinator, data)

    asyncio.run(switch.async_turn_on() if turn_on else switch.async_turn_off())

    expected = state.set_value("device_state_on" if turn_on else "device_state_off")
    assert [payload for _, payload in client.writes] == [
        bytearray([2, 4, 0, 4, 0, expected.index, 1, expected.value])
    ]
    # Write index 34 and the values 10 (on) and 20 (off) of this layout
    assert client.writes[0][1] == bytearray([2, 4, 0, 4, 0, 34, 1, last_byte])


def test_dishwasher_power_switch_follows_its_states() -> None:
    data = _entry_data(*DISHWASHER, appliance_type=3)
    state, _ = _controls(data)
    coordinator = _coordinator(None)
    switch = _power_switch(coordinator, data)

    for state_name in state.options.values():
        coordinator.data = _packet(data, state_name)
        assert switch.is_on is (state_name != "device_state_off"), state_name
        assert switch.available, state_name

    coordinator.data = _packet(data, "device_state_off")
    asyncio.run(switch.async_turn_on())
    coordinator.send_command.assert_awaited_once_with(
        state.set_value("device_state_on")
    )
    coordinator.send_command.reset_mock()
    coordinator.data = _packet(data, "device_state_cancelling")
    asyncio.run(switch.async_turn_off())
    coordinator.send_command.assert_awaited_once_with(
        state.set_value("device_state_off")
    )


def _setup_entry(appliance_type: int | None) -> tuple[Mock, Mock]:
    entry = Mock()
    entry.entry_id = "test_setup"
    entry.title = "Test"
    entry.data = {
        "contents": {
            "config": json.loads((FIXTURES / DRYER[0]).read_text()),
            "localization": {},
        },
        "appliance_info": None
        if appliance_type is None
        else dataclasses.asdict(_info(DRYER[1], appliance_type=appliance_type)),
        "ids": {"appId": "app"},
    }
    hass = Mock()
    hass.data = {DOMAIN: {"test_setup": _coordinator(None)}}
    add_entities = Mock()
    asyncio.run(async_setup_entry(hass, entry, add_entities))
    return add_entities, entry


@pytest.mark.parametrize("appliance_type", [5, 3])  # dryer, dishwasher
def test_setup_entry_adds_the_power_switch_next_to_the_other_switches(
    appliance_type: int,
) -> None:
    add_entities, _ = _setup_entry(appliance_type)

    added = add_entities.call_args.args[0]
    assert [type(entity) for entity in added].count(PowerSwitch) == 1
    assert any(isinstance(entity, HomeWhizSwitchEntity) for entity in added)


# washer, fridge, oven, hob, unknown
@pytest.mark.parametrize("appliance_type", [1, 2, 4, 7, None])
def test_setup_entry_adds_no_power_switch_for_other_appliances(
    appliance_type: int | None,
) -> None:
    add_entities, _ = _setup_entry(appliance_type)

    added = add_entities.call_args.args[0]
    assert not any(isinstance(entity, PowerSwitch) for entity in added)


def test_power_switch_has_names_and_an_icon() -> None:
    icons = json.loads((INTEGRATION / "icons.json").read_text())["entity"]["switch"]
    assert icons[POWER_KEY]["default"] == "mdi:power"
    assert icons[POWER_KEY]["state"] == {"off": "mdi:power-off"}
    for language in ("en", "de"):
        translations = json.loads(
            (INTEGRATION / "translations" / f"{language}.json").read_text()
        )["entity"]["switch"]
        assert translations[POWER_KEY]["name"]
