import logging
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any, Callable, Optional, TypeVar

from bidict import bidict

from custom_components.homewhiz.appliance_config import (
    ApplianceConfiguration,
    ApplianceFeature,
    ApplianceFeatureBoundedOption,
    ApplianceFeatureEnumOption,
    ApplianceProgram,
    ApplianceProgress,
    ApplianceProgressFeature,
    ApplianceState,
    ApplianceSubState,
)
from custom_components.homewhiz.helper import unit_for_key

from .homewhiz import Command

_LOGGER: logging.Logger = logging.getLogger(__package__)


def clamp(value: int):
    return value if value < 128 else value - 128


@dataclass
class Control:
    key: str
    get_value: Callable[[bytearray], Any]


Options = TypeVar("Options", bound=Mapping[int, str])


class EnumControl(Control):
    def __init__(self, key: str, read_index: int, options: Options):
        self.key = key
        self.read_index = read_index
        self.options = options

    def get_value(self, data: bytearray) -> str | None:
        byte = clamp(data[self.read_index])
        if byte in self.options:
            return self.options[byte]
        return None


class WriteEnumControl(EnumControl):
    def __init__(
        self, key: str, read_index: int, write_index: int, options: bidict[int, str]
    ):
        super().__init__(key, read_index, options)
        self.write_index = write_index

    def set_value(self, value: str) -> Command:
        byte = self.options.inverse[value]
        return Command(self.write_index, byte)


class NumericControl(Control):
    def __init__(
        self, key: str, read_index: int, bounds: ApplianceFeatureBoundedOption
    ):
        self.key = key
        self.read_index = read_index
        self.bounds = bounds

    def get_value(self, data: bytearray) -> float | None:
        byte = clamp(data[self.read_index])
        return byte * self.bounds.factor


class WriteNumericControl(NumericControl):
    def __init__(
        self,
        key: str,
        read_index: int,
        write_index: int,
        bounds: ApplianceFeatureBoundedOption,
    ):
        super().__init__(key, read_index, bounds)
        self.write_index = write_index

    def set_value(self, value: float) -> Command:
        return Command(index=self.write_index, value=int(value / self.bounds.factor))


class TimeControl(Control):
    def __init__(self, key: str, hour_index: int, minute_index: Optional[int]):
        self.key = key
        self.hour_index = hour_index
        self.minute_index = minute_index

    def get_value(self, data: bytearray) -> int:
        hours = clamp(data[self.hour_index])
        minutes = clamp(data[self.minute_index]) if self.minute_index is not None else 0
        return hours * 60 + minutes


@dataclass
class BooleanControl(Control):
    get_value: Callable[[bytearray], bool]


@dataclass
class WriteBooleanControl(Control):
    def __init__(
        self, key: str, read_index: int, write_index: int, value_on: int, value_off: int
    ):
        self.key = key
        self.read_index = read_index
        self.write_index = write_index
        self.value_on = value_on
        self.value_off = value_off

    def get_value(self, data: bytearray) -> bool:
        byte = clamp(data[self.read_index])
        return byte == self.value_on

    def set_value(self, value: bool) -> Command:
        return Command(
            index=self.write_index, value=self.value_on if value else self.value_off
        )


class ClimateControl(BooleanControl):
    key = "AC"

    def __init__(
        self,
        state: WriteBooleanControl,
        program: WriteEnumControl,
        target_temperature: WriteNumericControl,
        current_temperature: NumericControl,
        fan_mode: WriteEnumControl,
    ):
        self.state = state
        self.program = program
        self.target_temperature = target_temperature
        self.current_temperature = current_temperature
        self.fan_mode = fan_mode
        self.controls = [
            state,
            program,
            target_temperature,
            current_temperature,
            fan_mode,
        ]

    def get_value(self, data: bytearray):
        return {c.key: c.get_value(data) for c in self.controls}


def get_bounded_values_options(
    key: str, values: ApplianceFeatureBoundedOption
) -> bidict[int, str]:
    result: bidict[int, str] = bidict()
    value = values.lowerLimit
    while value <= values.upperLimit:
        wifiValue = int(value / values.factor)
        unit = unit_for_key(key)
        name = f"{value} {unit}" if unit is not None else str(value)
        result[wifiValue] = name
        value += values.step
    return result


def get_options_from_feature(feature: ApplianceFeature) -> bidict[int, str]:
    options: bidict[int, str] = bidict()
    if feature.enumValues is not None:
        options = options | {
            option.wifiArrayValue: option.strKey for option in feature.enumValues
        }
    if feature.boundedValues is not None:
        for boundedValues in feature.boundedValues:
            options = (
                get_bounded_values_options(feature.strKey, boundedValues) | options
            )
    return options


def get_options_from_enum_options(
    options: list[ApplianceFeatureEnumOption],
) -> dict[int, str]:
    return {option.wifiArrayValue: option.strKey for option in options}


def build_read_control_from_feature(feature: ApplianceFeature) -> Control:
    if (
        feature.enumValues is None
        and feature.boundedValues is not None
        and len(feature.boundedValues) == 1
    ):
        return NumericControl(
            key=feature.strKey,
            read_index=feature.wifiArrayIndex,
            bounds=feature.boundedValues[0],
        )
    return EnumControl(
        key=feature.strKey,
        read_index=feature.wifiArrayIndex,
        options=get_options_from_feature(feature),
    )


def build_write_control_from_feature(feature: ApplianceFeature) -> Control:
    write_index = (
        feature.wfaWriteIndex
        if feature.wfaWriteIndex is not None
        else feature.wifiArrayIndex
    )
    if (
        feature.enumValues is None
        and feature.boundedValues is not None
        and len(feature.boundedValues) == 1
    ):
        return WriteNumericControl(
            key=feature.strKey,
            read_index=feature.wifiArrayIndex,
            write_index=write_index,
            bounds=feature.boundedValues[0],
        )
    return WriteEnumControl(
        key=feature.strKey,
        read_index=feature.wifiArrayIndex,
        write_index=write_index,
        options=get_options_from_feature(feature),
    )


def build_control_from_program(program: ApplianceProgram) -> Control:
    return WriteEnumControl(
        key=program.strKey,
        read_index=program.wifiArrayIndex,
        write_index=(
            program.wfaWriteIndex
            if program.wfaWriteIndex is not None
            else program.wifiArrayIndex
        ),
        options=bidict(get_options_from_enum_options(program.values)),
    )


def build_control_from_substate(sub_states: Optional[ApplianceSubState]):
    if sub_states is None:
        return None
    return EnumControl(
        key="SUB_STATE",
        read_index=sub_states.wifiArrayReadIndex,
        options=get_options_from_enum_options(sub_states.subStates),
    )


def build_controls_from_monitorings(
    monitorings: Optional[list[ApplianceFeature]],
):
    if monitorings is None:
        return []
    return map(build_read_control_from_feature, monitorings)


def build_control_from_state(state: Optional[ApplianceState]) -> Optional[Control]:
    if state is None:
        return None
    return WriteEnumControl(
        key="STATE",
        read_index=state.wifiArrayReadIndex,
        write_index=(
            state.wifiArrayWriteIndex
            if state.wifiArrayWriteIndex is not None
            else state.wfaIndex
        ),
        options=bidict(get_options_from_enum_options(state.states)),
    )


def build_controls_from_progress_variables(
    progress_variables: Optional[ApplianceProgress],
):
    if progress_variables is None:
        return []
    result = []
    for field in fields(progress_variables):
        feature: Optional[ApplianceProgressFeature] = getattr(
            progress_variables, field.name
        )
        if feature is not None:
            result.append(
                TimeControl(
                    key=feature.strKey,
                    hour_index=feature.hour.wifiArrayIndex,
                    minute_index=feature.minute.wifiArrayIndex
                    if feature.minute is not None
                    else None,
                )
            )
    return result


def convert_to_bool_control_if_possible(control: Control) -> Control:
    if not isinstance(control, WriteEnumControl):
        return control
    options = control.options.inverse
    option_keys = list(options.keys())
    option_keys.sort()
    if (
        len(option_keys) == 2
        and option_keys[0].endswith("_OFF")
        and option_keys[1].endswith("_ON")
    ):
        return WriteBooleanControl(
            key=control.key,
            read_index=control.read_index,
            write_index=control.write_index,
            value_off=options[option_keys[0]],
            value_on=options[option_keys[1]],
        )
    return control


def extract_ac_control(controls: list[Control]) -> list[Control]:
    controls_dict = {control.key: control for control in controls}
    keys = controls_dict.keys()
    if "AIR_CONDITIONER_PROGRAM" in keys:
        climate = ClimateControl(
            state=controls_dict["STATE"],
            program=controls_dict["AIR_CONDITIONER_PROGRAM"],
            current_temperature=controls_dict["AIR_CONDITIONER_ROOM_TEMPERATURE"],
            target_temperature=controls_dict["AIR_CONDITIONER_TARGET_TEMPERATURE"],
            fan_mode=controls_dict["AIR_CONDITIONER_WIND_STRENGTH"],
        )
        return [c for c in controls if c not in climate.controls] + [climate]
    return controls


def generate_controls_from_config(
    config: ApplianceConfiguration,
) -> list[Control]:
    controls = [
        build_control_from_state(config.deviceStates),
        build_control_from_program(config.program),
        build_control_from_substate(config.deviceSubStates),
        *map(build_write_control_from_feature, config.subPrograms),
        *build_controls_from_monitorings(config.monitorings),
        *build_controls_from_progress_variables(config.progressVariables),
    ]
    controls = [
        convert_to_bool_control_if_possible(control)
        for control in controls
        if control is not None
    ]
    controls = extract_ac_control(controls)

    return controls
