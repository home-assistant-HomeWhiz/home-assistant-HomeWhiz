"""Tests for the cloud device selection step.

The flow handler is driven directly and async code runs through asyncio.run()
from sync tests, so no extra plugin is needed. Feeding it a prepared appliance
list requires touching private attributes.
"""

# ruff: noqa: SLF001

import asyncio
from typing import Any
from unittest.mock import Mock

from homeassistant.data_entry_flow import FlowResultType

from custom_components.homewhiz.api import ApplianceInfo
from custom_components.homewhiz.config_flow import TiltConfigFlow


def _appliance(appliance_id: str, connectivity: str) -> ApplianceInfo:
    return ApplianceInfo(
        id=1,
        applianceId=appliance_id,
        brand=1,
        model="model",
        applianceType=1,
        platformType="platform",
        applianceSerialNumber=None,
        name=f"Appliance {appliance_id}",
        hsmId=None,
        connectivity=connectivity,
    )


def _make_flow(appliances: list[ApplianceInfo]) -> TiltConfigFlow:
    flow = TiltConfigFlow()
    flow.flow_id = "test"
    flow.handler = "homewhiz"
    credentials: Any = Mock()  # the step only checks it is not None
    flow._cloud_credentials = credentials
    flow._cloud_appliances = appliances
    return flow


def test_bluetooth_only_account_aborts() -> None:
    """A cloud form with nothing to pick from is a dead end for the user."""
    flow = _make_flow([_appliance("a1", "BASICBT"), _appliance("a2", "BT")])

    result = asyncio.run(flow.async_step_select_cloud_device())

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_cloud_devices_found"


def test_empty_account_aborts() -> None:
    flow = _make_flow([])

    result = asyncio.run(flow.async_step_select_cloud_device())

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


def test_cloud_devices_are_offered() -> None:
    flow = _make_flow([_appliance("a1", "BASICBT"), _appliance("a2", "BTWIFI")])

    result = asyncio.run(flow.async_step_select_cloud_device())

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "select_cloud_device"
