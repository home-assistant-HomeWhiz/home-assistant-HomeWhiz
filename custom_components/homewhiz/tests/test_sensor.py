from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.homewhiz.api import ApplianceContents
from custom_components.homewhiz.appliance_config import ApplianceFeatureBoundedOption
from custom_components.homewhiz.appliance_controls import NumericControl
from custom_components.homewhiz.config_flow import EntryData
from custom_components.homewhiz.const import DOMAIN
from custom_components.homewhiz.sensor import HomeWhizSensorEntity


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
