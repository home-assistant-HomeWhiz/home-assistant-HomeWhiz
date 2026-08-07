"""Tests for HomeWhizSensorEntity and HomeWhizEnergyEntity.

Deliberately hass-free (project convention, see test_config_flow.py): the
async lifecycle methods here are exercised with Mock()-based coordinators
and monkeypatched RestoreSensor hooks rather than a real hass instance.
"""

# ruff: noqa: SLF001

import asyncio
import math
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorExtraStoredData,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.homewhiz.api import ApplianceContents
from custom_components.homewhiz.appliance_config import ApplianceFeatureBoundedOption
from custom_components.homewhiz.appliance_controls import NumericControl
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.const import DOMAIN
from custom_components.homewhiz.sensor import (
    INSTANT_CONSUMPTION_BOGUS_UNIT,
    INSTANT_CONSUMPTION_KEY,
    MAX_INTEGRATION_GAP_HOURS,
    HomeWhizEnergyEntity,
    HomeWhizSensorEntity,
    _find_instant_consumption_controls,
)


def _entry_data() -> EntryData:
    return EntryData(
        ids=Mock(),
        contents=ApplianceContents(config=Mock(), localization={}),
        appliance_info=None,
        cloud_config=None,
    )


def test_instant_consumption_sensor_reports_kw_power_measurement() -> None:
    control = NumericControl(
        key="air_conditioner_instant_consumption",
        read_index=45,
        bounds=ApplianceFeatureBoundedOption(
            factor=0.1,
            lowerLimit=0,
            step=1,
            strKey="",
            unit="hw",
            upperLimit=500,
        ),
    )

    entity = HomeWhizSensorEntity(
        coordinator=Mock(),
        control=control,
        device_name="Test AC",
        data=_entry_data(),
    )

    assert entity.native_unit_of_measurement == "kW"
    assert entity.device_class == SensorDeviceClass.POWER
    assert entity.state_class == SensorStateClass.MEASUREMENT


def test_unrelated_numeric_control_sensor_keeps_previous_behavior() -> None:
    """Only the instant_consumption key should get the kW/POWER/MEASUREMENT
    treatment - any other NumericControl (e.g. room temperature) must not
    get an explicit native_unit_of_measurement or device_class assigned by
    HomeWhizSensorEntity, matching pre-existing (pre-fix) behavior."""
    control = NumericControl(
        key="air_conditioner_room_temperature",
        read_index=40,
        bounds=ApplianceFeatureBoundedOption(
            factor=0.5,
            lowerLimit=0,
            step=0.5,
            strKey="",
            unit="°C",
            upperLimit=100,
        ),
    )

    entity = HomeWhizSensorEntity(
        coordinator=Mock(),
        control=control,
        device_name="Test AC",
        data=_entry_data(),
    )

    assert entity.native_unit_of_measurement is None
    # HomeWhizEntity's base __init__ always sets a homewhiz-internal
    # placeholder device_class (f"{DOMAIN}__{entity_key}") that no branch
    # in HomeWhizSensorEntity overrides for this control - this is the
    # pre-existing (pre-fix) behavior for any NumericControl other than
    # the one instant_consumption key, left untouched by this PR.
    assert entity.device_class == f"{DOMAIN}__{control.key}"
    assert entity.state_class is None


def test_instant_consumption_sensor_with_a_real_unit_is_left_alone() -> None:
    """The known-bad signature is the key plus the bogus "hw" unit label. A
    device reporting the same key with a real unit must keep its previous
    behavior, matching the factor correction in extract_ac_control."""
    control = NumericControl(
        key="air_conditioner_instant_consumption",
        read_index=45,
        bounds=ApplianceFeatureBoundedOption(
            factor=1,
            lowerLimit=0,
            step=1,
            strKey="",
            unit="W",
            upperLimit=500,
        ),
    )

    entity = HomeWhizSensorEntity(
        coordinator=Mock(),
        control=control,
        device_name="Test AC",
        data=_entry_data(),
    )

    assert entity.native_unit_of_measurement is None
    assert entity.device_class == f"{DOMAIN}__{control.key}"
    assert entity.state_class is None


def _power_control(read_index: int = 45) -> NumericControl:
    return NumericControl(
        key=INSTANT_CONSUMPTION_KEY,
        read_index=read_index,
        bounds=ApplianceFeatureBoundedOption(
            factor=0.1,
            lowerLimit=0,
            step=1,
            strKey="",
            unit=INSTANT_CONSUMPTION_BOGUS_UNIT,
            upperLimit=500,
        ),
    )


def _energy_entity(coordinator: Mock | None = None) -> HomeWhizEnergyEntity:
    if coordinator is None:
        coordinator = Mock()
        coordinator.data = bytearray(60)
    return HomeWhizEnergyEntity(
        coordinator=coordinator,
        power_control=_power_control(),
        device_name="Test AC",
        data=_entry_data(),
    )


def test_energy_entity_reports_energy_device_class_and_kwh_unit() -> None:
    """Regression test: HomeWhizEntity.__init__ unconditionally sets a
    homewhiz-internal placeholder device_class, which previously clobbered
    the ENERGY device_class on this entity (silently rejected by the HA
    Energy dashboard as "Unexpected device class")."""
    entity = _energy_entity()

    assert entity.device_class == SensorDeviceClass.ENERGY
    assert entity.state_class == SensorStateClass.TOTAL
    assert entity.native_unit_of_measurement == "kWh"
    assert entity.native_value == 0.0


def test_energy_entity_translation_key_is_none() -> None:
    """No translation entry exists for the generated "..._total" key, and
    scripts/generate_translations.py would drop a manual one on its next
    run - translation_key must be overridden to None so HA falls back to
    the device class name instead of showing the raw, untranslated key."""
    entity = _energy_entity()

    assert entity.translation_key is None


@pytest.mark.parametrize(
    ("native_value", "expected"),
    [
        (None, 0.0),
        (12.5, 12.5),
        (12, 12.0),
        (0, 0.0),
        ("12.5", 12.5),
        ("not-a-number", 0.0),
        (float("nan"), 0.0),
        (float("inf"), 0.0),
        (float("-inf"), 0.0),
    ],
)
def test_parse_restored_total(
    native_value: float | str | None, expected: float
) -> None:
    assert HomeWhizEnergyEntity.parse_restored_total(native_value) == expected


def test_integrate_delta_with_no_previous_sample_is_a_no_op() -> None:
    assert HomeWhizEnergyEntity.integrate_delta(None, 1.0, 1.0) == 0.0


def test_integrate_delta_normal_step() -> None:
    # 0.4 kW average over 0.5h -> 0.2 kWh
    delta = HomeWhizEnergyEntity.integrate_delta(0.3, 0.5, 0.5)
    assert delta == pytest.approx(0.2)


def test_integrate_delta_skips_gap_larger_than_threshold() -> None:
    """A gap since HA was last running (or the appliance was offline)
    should not be integrated as if power were constant that whole time."""
    delta = HomeWhizEnergyEntity.integrate_delta(
        0.5, 0.5, MAX_INTEGRATION_GAP_HOURS + 0.01
    )
    assert delta == 0.0


def test_integrate_delta_at_exactly_the_threshold_is_still_integrated() -> None:
    delta = HomeWhizEnergyEntity.integrate_delta(0.5, 0.5, MAX_INTEGRATION_GAP_HOURS)
    assert delta == pytest.approx(0.5 * MAX_INTEGRATION_GAP_HOURS)


def test_integrate_delta_zero_or_negative_elapsed_is_a_no_op() -> None:
    assert HomeWhizEnergyEntity.integrate_delta(0.5, 0.5, 0.0) == 0.0
    assert HomeWhizEnergyEntity.integrate_delta(0.5, 0.5, -1.0) == 0.0


def test_advance_integration_accumulates_over_two_steps() -> None:
    """Two pushes with a controlled clock must accumulate the trapezoidal
    energy for each step."""
    coordinator = Mock()
    coordinator.data = bytearray(60)
    coordinator.data[45] = 4  # 4 * 0.1 = 0.4 kW

    entity = _energy_entity(coordinator)
    entity._last_update = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    entity._last_power_kw = 0.4

    # Second sample, 30 minutes later, power unchanged at 0.4 kW.
    entity._advance_integration(datetime(2026, 1, 1, 12, 30, 0, tzinfo=UTC))

    # 0.4 kW constant for 0.5h -> 0.2 kWh
    assert entity.native_value == pytest.approx(0.2)
    assert entity._last_power_kw == 0.4


def test_advance_integration_clears_baseline_on_missing_data() -> None:
    """When the coordinator data disappears, the integration baseline must
    be cleared entirely, not just left in place - otherwise the *next*
    valid sample would integrate across the whole gap as if power had
    been constant that entire time (fabricating energy never measured)."""
    coordinator = Mock()
    coordinator.data = None

    entity = _energy_entity(coordinator)
    entity._last_update = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    entity._last_power_kw = 0.4

    entity._advance_integration(datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC))

    assert entity.native_value == 0.0
    assert entity._last_power_kw is None
    assert entity._last_update is None


def test_advance_integration_valid_then_gap_then_valid_integrates_zero() -> None:
    """The scenario the previous (buggy) behavior got wrong: a valid
    sample, then a gap where the appliance/coordinator data is
    unavailable, then a valid sample again. No energy should be
    fabricated for the gap itself."""
    coordinator = Mock()
    coordinator.data = bytearray(60)
    coordinator.data[45] = 4  # 0.4 kW

    entity = _energy_entity(coordinator)

    # First valid sample.
    entity._advance_integration(datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))
    assert entity.native_value == 0.0  # nothing to integrate yet (no prior sample)

    # Gap: coordinator data goes missing for 5 minutes.
    coordinator.data = None
    entity._advance_integration(datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC))

    # Data comes back, still 0.4 kW.
    coordinator.data = bytearray(60)
    coordinator.data[45] = 4
    entity._advance_integration(datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC))

    # Previously: 0.4 kW * (10 min gap, wrongly measured as if constant)
    # would have fabricated ~0.0667 kWh. Correct behavior: 0, since there
    # was no valid sample immediately before this one (baseline was
    # cleared during the gap).
    assert entity.native_value == 0.0


def test_handle_coordinator_update_calls_advance_integration() -> None:
    """Wiring test: _handle_coordinator_update must feed a real clock
    reading into _advance_integration before deferring to the base
    CoordinatorEntity behavior (state write, which needs a real hass and
    is out of scope for this lightweight test suite)."""
    entity = _energy_entity()

    with (
        patch.object(HomeWhizEnergyEntity, "_advance_integration") as advance,
        patch.object(CoordinatorEntity, "_handle_coordinator_update"),
    ):
        entity._handle_coordinator_update()

    advance.assert_called_once()
    (called_now,) = advance.call_args.args
    assert isinstance(called_now, datetime)


def test_async_added_to_hass_restores_previous_total() -> None:
    entity = _energy_entity()
    entity.async_get_last_sensor_data = AsyncMock(  # type: ignore[method-assign]
        return_value=SensorExtraStoredData(
            native_value=42.5, native_unit_of_measurement="kWh"
        )
    )

    asyncio.run(entity.async_added_to_hass())

    assert entity.native_value == 42.5
    # Baseline for the next integration step must be primed too.
    assert entity._last_power_kw == pytest.approx(0.0)


def test_async_added_to_hass_survives_appliance_being_unavailable_at_shutdown() -> None:
    """The bug this replaces: RestoreEntity restores the *published state
    string*, which HA forces to "unavailable" whenever the entity's
    `available` property was False (e.g. the appliance was offline right
    before HA shut down) - even though the real accumulated total was a
    valid positive number. RestoreSensor stores native_value separately
    from the published state, so it isn't affected by that at all."""
    entity = _energy_entity()
    entity.async_get_last_sensor_data = AsyncMock(  # type: ignore[method-assign]
        return_value=SensorExtraStoredData(
            native_value=17.25, native_unit_of_measurement="kWh"
        )
    )

    asyncio.run(entity.async_added_to_hass())

    assert entity.native_value == 17.25


def test_async_added_to_hass_with_no_previous_state_starts_at_zero() -> None:
    entity = _energy_entity()
    entity.async_get_last_sensor_data = AsyncMock(return_value=None)  # type: ignore[method-assign]

    asyncio.run(entity.async_added_to_hass())

    assert entity.native_value == 0.0


def test_find_instant_consumption_controls_matches_only_the_known_signature() -> None:
    matching = _power_control()
    wrong_unit = NumericControl(
        key=INSTANT_CONSUMPTION_KEY,
        read_index=45,
        bounds=ApplianceFeatureBoundedOption(
            factor=1, lowerLimit=0, step=1, strKey="", unit="W", upperLimit=500
        ),
    )
    wrong_key = NumericControl(
        key="air_conditioner_room_temperature",
        read_index=40,
        bounds=ApplianceFeatureBoundedOption(
            factor=0.5,
            lowerLimit=0,
            step=0.5,
            strKey="",
            unit=INSTANT_CONSUMPTION_BOGUS_UNIT,
            upperLimit=100,
        ),
    )

    result = _find_instant_consumption_controls([matching, wrong_unit, wrong_key])

    assert result == [matching]


@pytest.mark.parametrize(
    "coordinator_data",
    [
        None,
        bytearray(),
        bytearray(10),  # shorter than read_index (45)
    ],
    ids=["none", "empty-bytearray", "short-bytearray"],
)
def test_advance_integration_never_raises_on_bad_coordinator_data(
    coordinator_data: bytearray | None,
) -> None:
    """A misbehaving/short-lived coordinator payload must never raise here:
    coordinator listeners run without per-listener exception handling in
    HA, so an exception in this entity would prevent any other listener
    scheduled in the same update cycle from running."""
    coordinator = Mock()
    coordinator.data = coordinator_data

    entity = _energy_entity(coordinator)
    entity._last_update = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    entity._last_power_kw = 0.4

    entity._advance_integration(datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC))

    # The point of this test is that none of these inputs raise. safe_get()
    # treats out-of-range/missing bytes as 0 (not an error), so an empty or
    # short bytearray still yields a (zero-byte) reading and integrates
    # normally; only coordinator.data being None short-circuits before any
    # byte access happens. Either way, the result must stay a finite float.
    assert math.isfinite(entity.native_value)
