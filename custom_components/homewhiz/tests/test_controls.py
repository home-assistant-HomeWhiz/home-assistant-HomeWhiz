import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase

import pytest
from dacite import from_dict

from custom_components.homewhiz.appliance_config import (
    ApplianceConfiguration,
    ApplianceFeatureBoundedOption,
)
from custom_components.homewhiz.appliance_controls import (
    EnumControl,
    WriteBooleanControl,
    WriteEnumControl,
    WriteTimeControl,
    build_control_from_program,
    controls,
    forget_controls,
    generate_controls_from_config,
    get_bounded_values_options,
    to_friendly_name,
)
from custom_components.homewhiz.homewhiz import Command

test_case = TestCase()
test_case.maxDiff = None


@pytest.fixture
def config() -> ApplianceConfiguration:
    file_path = (
        Path(__file__).parent / "fixtures" / "example_washing_machine_config.json"
    )
    with file_path.open() as file:
        json_content = json.load(file)
        return from_dict(ApplianceConfiguration, json_content)


def test_options_order(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_controls", config)
    controls_map = {control.key: control for control in controls}
    assert "washer_temperature" in controls_map
    temp_control = controls_map["washer_temperature"]
    assert isinstance(temp_control, EnumControl)
    test_case.assertListEqual(
        list(temp_control.options.values()),
        [
            "temperature_cold_wash",
            "temperature_20",
            "temperature_30",
            "temperature_40",
            "60c",
            "90c",
        ],
    )


def test_writable_start_delay(config: ApplianceConfiguration) -> None:
    controls = generate_controls_from_config("test_writable_start_delay", config)
    controls_map = {control.key: control for control in controls}

    # Writable counterpart of the read-only "delay_start#0" sensor.
    assert "delay_start_set#0" in controls_map
    delay = controls_map["delay_start_set#0"]
    assert isinstance(delay, WriteTimeControl)
    assert delay.minute_index is not None

    # 125 minutes -> 2h 5m, written to the hour and minute bytes.
    assert delay.set_value(125) == [
        Command(delay.hour_index, 2),
        Command(delay.minute_index, 5),
    ]

    # Negative values are clamped to zero.
    assert delay.set_value(-10) == [
        Command(delay.hour_index, 0),
        Command(delay.minute_index, 0),
    ]

    # Written commands round-trip through get_value.
    data = bytearray(max(delay.hour_index, delay.minute_index) + 1)
    for command in delay.set_value(125):
        data[command.index] = command.value
    assert delay.get_value(data) == 125


def test_program_options_with_duplicate_names() -> None:
    # Issue #410: this Beko washer lists PROGRAM_MIX twice (bytes 7 and 16),
    # which crashed every platform setup with bidict.ValueDuplicationError.
    # The duplicate gets the wifiArrayValue suffixed instead, like the existing
    # guard in get_options_from_feature (#273).
    file_path = Path(__file__).parent / "fixtures" / "beko-washer-410.json"
    with file_path.open(encoding="utf-8") as file:
        washer_config = from_dict(ApplianceConfiguration, json.load(file))
    control = build_control_from_program(washer_config.program)
    assert isinstance(control, WriteEnumControl)
    options = list(control.options.values())
    assert len(options) == 21
    assert "program_mix" in options
    assert "program_mix_16" in options
    # Both names stay individually writable: the first entry keeps the plain
    # name (byte 7), the duplicate carries its byte value as suffix.
    assert control.set_value("program_mix") == Command(control.write_index, 7)
    assert control.set_value("program_mix_16") == Command(control.write_index, 16)


def _bounded(step: float, factor: float) -> ApplianceFeatureBoundedOption:
    return ApplianceFeatureBoundedOption(
        factor=factor,
        lowerLimit=0,
        step=step,
        strKey="TEMPERATURE",
        unit=None,
        upperLimit=4,
    )


def test_bounded_values_are_expanded() -> None:
    options = get_bounded_values_options("temperature", _bounded(step=2, factor=1))

    assert list(options.items()) == [(0, "0c"), (2, "2c"), (4, "4c")]


def test_zero_step_is_skipped() -> None:
    """A step of zero would otherwise loop forever and freeze the event loop."""
    assert len(get_bounded_values_options("temperature", _bounded(0, 1))) == 0


def test_zero_factor_is_skipped() -> None:
    """A factor of zero would otherwise raise ZeroDivisionError during setup."""
    assert len(get_bounded_values_options("temperature", _bounded(1, 0))) == 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Program_", "program"),
        ("Program", "program"),
        ("Temp+", "tempplus"),
        ("-18 °C", "-18c"),
        ("!!!", ""),
        ("", ""),
    ],
)
def test_to_friendly_name(raw: str, expected: str) -> None:
    assert to_friendly_name(raw) == expected


def test_forget_controls_removes_the_cached_entry(
    config: ApplianceConfiguration,
) -> None:
    key = "test-entry-forget-controls"
    first = generate_controls_from_config(key, config)
    assert key in controls

    forget_controls(key)

    assert key not in controls
    # A rebuilt list, not the same cached object handed back again.
    assert generate_controls_from_config(key, config) is not first
    forget_controls(key)  # do not leak state into other tests


def test_forget_controls_on_unknown_key_is_a_no_op() -> None:
    forget_controls("never-generated")


def test_duplicate_controls_keep_first_occurrence_and_order(
    config: ApplianceConfiguration,
) -> None:
    assert config.subPrograms is not None
    steam = next(f for f in config.subPrograms if f.strKey == "WASHER_STEAM")
    # Issue #452: one feature appears in two config branches. Different indices
    # make retaining the wrong occurrence observable, not just its key.
    duplicate_config = ApplianceConfiguration(
        subPrograms=[steam, replace(steam, strKey="WASHER_OTHER")],
        settings=[replace(steam, wifiArrayIndex=98, wfaWriteIndex=99)],
    )
    key = "test-duplicate-controls"
    try:
        generated = generate_controls_from_config(key, duplicate_config)
        # Assert on the list: a dict keyed by control.key would hide the bug.
        assert [(type(c), c.key) for c in generated] == [
            (WriteBooleanControl, "washer_steam"),
            (WriteBooleanControl, "washer_other"),
        ]
        first = generated[0]
        assert isinstance(first, WriteBooleanControl)
        assert first.read_index == steam.wifiArrayIndex
        assert first.set_value(True) == Command(steam.wifiArrayIndex, 1)
        assert first.set_value(False) == Command(steam.wifiArrayIndex, 0)
        assert generate_controls_from_config(key, duplicate_config) is generated
    finally:
        forget_controls(key)


def test_same_key_controls_of_different_classes_are_preserved(
    config: ApplianceConfiguration,
) -> None:
    assert config.subPrograms is not None
    steam = next(f for f in config.subPrograms if f.strKey == "WASHER_STEAM")
    shared_key_config = ApplianceConfiguration(
        subPrograms=[steam], monitorings=[steam], settings=[steam]
    )
    key = "test-shared-control-key"
    try:
        generated = generate_controls_from_config(key, shared_key_config)
        assert [(type(c), c.key) for c in generated] == [
            (WriteBooleanControl, "washer_steam"),
            (EnumControl, "washer_steam"),
        ]
    finally:
        forget_controls(key)
