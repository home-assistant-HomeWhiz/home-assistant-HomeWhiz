"""Tests for the cloud device selection step.

The flow handler is driven directly and async code runs through asyncio.run()
from sync tests, so no extra plugin is needed. Feeding it a prepared appliance
list requires touching private attributes.
"""

# ruff: noqa: SLF001

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import CONF_ID
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homewhiz.api import ApplianceContents, ApplianceInfo
from custom_components.homewhiz.appliance_config import ApplianceConfiguration
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


def _submittable_flow(appliances: list[ApplianceInfo]) -> TiltConfigFlow:
    """The submit path calls Home Assistant's unique id helpers, which need a
    running hass. Stub them out. That keeps these tests on the step's own
    behaviour, and it means they say nothing about Home Assistant's abort
    semantics for an id that is already claimed or configured."""
    flow = _make_flow(appliances)
    flow.async_set_unique_id = AsyncMock(return_value=None)  # type: ignore[method-assign]
    flow._abort_if_unique_id_configured = Mock(return_value=None)  # type: ignore[method-assign]
    return flow


def test_failing_contents_fetch_shows_the_form_again() -> None:
    """Issue #451 ended in this step with a traceback and a dead end."""
    flow = _submittable_flow([_appliance("a1", "BTWIFI")])

    with patch(
        "custom_components.homewhiz.config_flow.fetch_appliance_contents",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = asyncio.run(flow.async_step_select_cloud_device({CONF_ID: "a1"}))

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "select_cloud_device"
    assert result["errors"] == {"base": "unknown"}


def test_a_caught_error_leaves_the_flow_usable() -> None:
    """A second submit after a caught fetch error still creates the entry, so
    the except branch does not leave the step in a state it cannot recover
    from."""
    flow = _submittable_flow([_appliance("a1", "BTWIFI")])
    contents = ApplianceContents(config=ApplianceConfiguration(), localization={})

    with patch(
        "custom_components.homewhiz.config_flow.fetch_appliance_contents",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        failed = asyncio.run(flow.async_step_select_cloud_device({CONF_ID: "a1"}))

    assert failed["type"] == FlowResultType.FORM

    with patch(
        "custom_components.homewhiz.config_flow.fetch_appliance_contents",
        AsyncMock(return_value=contents),
    ):
        result = asyncio.run(flow.async_step_select_cloud_device({CONF_ID: "a1"}))

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Appliance a1"
