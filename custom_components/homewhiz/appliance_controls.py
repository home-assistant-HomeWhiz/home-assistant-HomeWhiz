import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from typing import Any, Generic, TypeVar

from bidict import bidict
from homeassistant.components.climate import (  # type: ignore[import]
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    HVACMode,
)

from custom_components.homewhiz.appliance_config import (
    ApplianceConfiguration,
    ApplianceFeature,
    ApplianceFeatureBoundedOption,
    ApplianceFeatureEnumOption,
    ApplianceProgram,
    ApplianceProgress,
    ApplianceProgressFeature,
    ApplianceRemoteControl,
    ApplianceState,
    ApplianceSubState,
    ApplianceWarning,
)
from custom_components.homewhiz.helper import unit_for_key

from .homewhiz import Command

_LOGGER: logging.Logger = logging.getLogger(__package__)


def clamp(value: int) -> int:
    return value if value < 128 else value - 128


def to_friendly_name(name: str) -> str:
    # Generates a translation friendly name based on the key
    # To filter out characters not supported by homeassistant
    name = name.replace("+", "plus")
    name = name.lower()
    # https://stackoverflow.com/questions/15754587/keeping-only-certain-characters-in-a-string-using-python
    name = re.sub("[^a-z0-9-_]", "", name)
    # "cannot start or end with a hyphen or underscore
    if name[-1] == "_":
        name = name[:-1]
    return name


class Control(ABC):
    """Parent control class"""

    key: str

    def get_value(self, data: bytearray) -> Any:
        pass

    @property
    def friendly_name(self) -> str:
        return to_friendly_name(self.key)


class Option(ABC):
    """General option class"""

    value: int
    name: str

    def get_value(self, data: bytearray) -> Any:
        pass

    @property
    def friendly_name(self) -> str:
        return to_friendly_name(self.name)


class DebugControl(Control):
    def __init__(self, key: str, read_index: int):
        self.key = key
        self.read_index = read_index

    def get_value(self, data: bytearray) -> Any:
        return data[self.read_index]


_Options = TypeVar("_Options", bound=Mapping[int, str])


class EnumControl(Control, Generic[_Options]):
    """Control class for enum sensors"""

    def __init__(self, key: str, read_index: int, options: _Options):
        self.key = key
        self.read_index = read_index
        self.options = options

    def get_value(self, data: bytearray) -> str | None:
        byte = clamp(data[self.read_index])
        if byte in self.options:
            return self.options[byte]
        return None


class WriteEnumControl(EnumControl[bidict[int, str]]):
    """Control class for enum selectors"""

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
    def __init__(self, key: str, hour_index: int, minute_index: int | None):
        self.key = key
        self.hour_index = hour_index
        self.minute_index = minute_index

    def get_value(self, data: bytearray) -> int:
        hours = clamp(data[self.hour_index])
        minutes = clamp(data[self.minute_index]) if self.minute_index is not None else 0
        return hours * 60 + minutes


class SummedTimestampControl(Control):
    """Uses different sensors to calculate a timestamp"""

    def __init__(self, key: str, sensors: list[Control]):
        self.key = key
        # Sensors used for timestamp calculation
        self.sensors = sensors

    def get_value(self, data: bytearray) -> datetime | None:
        _LOGGER.debug(
            "Calculating Time for %s from %s",
            self.key,
            [sensor.key for sensor in self.sensors],
        )
        # Calculate timestamps for delay_start_time and delay_end_time
        # delay_start_time: Sensors are washer_delay and washer_remaining
        # delay_end_time: Sensors are washer_delay
        minute_delta = sum([sensor.get_value(data) for sensor in self.sensors])
        if minute_delta < 1:
            _LOGGER.debug("Device Running or No Delay Active")
            return None

        time_delta = timedelta(minutes=minute_delta)
        _LOGGER.debug("Calculated time delta of %s", time_delta)
        time_est = (
            datetime.now(timezone.utc).replace(second=0, microsecond=0) + time_delta
        )
        _LOGGER.debug("Calculated time of %s", time_est)
        return time_est


class BooleanControl(Control):
    @abstractmethod
    def get_value(self, data: bytearray) -> bool:
        pass


class BooleanCompareControl(BooleanControl):
    def __init__(self, key: str, read_index: int, compare_value: int):
        self.key = key
        self.read_index = read_index
        self.compare_value = compare_value

    def get_value(self, data: bytearray) -> bool:
        return data[self.read_index] == self.compare_value


class BooleanBitmaskControl(BooleanControl):
    def __init__(self, key: str, read_index: int, bit: int):
        self.key = key
        self.read_index = read_index
        self.bit = bit

    def get_value(self, data: bytearray) -> bool:
        return data[self.read_index] & (1 << self.bit) != 0


@dataclass
class WriteBooleanControl(BooleanControl):
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


class DisabledSwingAxisControl(Control):
    key = "disabled"
    enabled = False

    def get_value(self, data: bytearray) -> bool:
        return False

    def set_value(self, value: bool, current_data: bytearray) -> list[Command]:
        return []


class SwingAxisControl(Control):
    enabled = True

    def __init__(self, parent: WriteEnumControl | WriteBooleanControl):
        self.key = parent.key
        self.parent = parent

    def get_value(self, data: bytearray) -> bool:
        option = self.parent.get_value(data)
        _LOGGER.debug("Option - type: %s value: %s", type(option), option)
        if isinstance(option, bool):
            return option
        return option is not None and not option.endswith("_off")

    def _option_with_suffix(self, suffix: str) -> str | None:
        if isinstance(self.parent, WriteBooleanControl):
            return None
        return next(
            (
                option
                for option in self.parent.options.values()
                if option.endswith(suffix)
            ),
            None,
        )

    def set_value(self, value: bool, current_data: bytearray) -> list[Command]:
        current_value = self.get_value(current_data)
        if current_value == value:
            return []
        if isinstance(self.parent, WriteBooleanControl):
            return [self.parent.set_value(value)]
        selected_option = (
            self._option_with_suffix("_auto")
            if value
            else self._option_with_suffix("_off")
        )
        if selected_option is None:
            raise Exception(f"Cannot change swing for axis {self.key}")
        return [self.parent.set_value(selected_option)]


def build_swing_control_from_optional(
    parent: WriteEnumControl | WriteBooleanControl | None,
) -> DisabledSwingAxisControl | SwingAxisControl:
    if parent is None:
        return DisabledSwingAxisControl()
    return SwingAxisControl(parent)


class SwingControl(Control):
    key = "swing"

    def __init__(
        self,
        horizontal: WriteEnumControl | None,
        vertical: WriteEnumControl | WriteBooleanControl | None,
    ):
        self.horizontal = build_swing_control_from_optional(horizontal)
        self.vertical = build_swing_control_from_optional(vertical)
        self.enabled = self.horizontal.enabled or self.vertical.enabled

    @property
    def options(self) -> list[str]:
        result: list[str] = [SWING_OFF]
        if self.horizontal.enabled:
            result.append(SWING_HORIZONTAL)
        if self.vertical.enabled:
            result.append(SWING_VERTICAL)
        if self.horizontal.enabled and self.vertical.enabled:
            result.append(SWING_BOTH)
        return result

    def get_value(self, data: bytearray) -> str:
        value_horizontal = self.horizontal.get_value(data)
        value_vertical = self.vertical.get_value(data)
        if value_horizontal and value_vertical:
            return SWING_BOTH
        if value_horizontal:
            return SWING_HORIZONTAL
        if value_vertical:
            return SWING_VERTICAL
        return SWING_OFF

    def set_value(self, value: str, current_data: bytearray) -> list[Command]:
        value_horizontal = value == SWING_HORIZONTAL or value == SWING_BOTH
        value_vertical = value == SWING_VERTICAL or value == SWING_BOTH
        return self.horizontal.set_value(
            value_horizontal, current_data
        ) + self.vertical.set_value(value_vertical, current_data)


program_suffix_to_hvac_mode = {
    "cooling": HVACMode.COOL,
    "auto": HVACMode.AUTO,
    "dry": HVACMode.DRY,
    "dehumidification": HVACMode.DRY,
    "heating": HVACMode.HEAT,
    "fan": HVACMode.FAN_ONLY,
}


class HvacControl(Control):
    key = "hvac"

    def __init__(self, program: WriteEnumControl, state: WriteBooleanControl):
        self.program = program
        self.state = state
        self._program_dict = bidict(
            {
                option: program_suffix_to_hvac_mode[option.split("_")[-1]]
                for option in program.options.values()
            }
        )

    def _hvac_mode_raw(self, data: bytearray) -> HVACMode | None:
        option = self.program.get_value(data)
        if option is None:
            return None
        return self._program_dict[option]

    def get_value(self, data: bytearray) -> HVACMode | None:
        if not self.state.get_value(data):
            return HVACMode.OFF
        return self._hvac_mode_raw(data)

    def set_value(self, hvac_mode: HVACMode, current_data: bytearray) -> list[Command]:
        if hvac_mode == HVACMode.OFF:
            return [self.state.set_value(False)]
        result: list[Command] = []
        if not self.state.get_value(current_data):
            result.append(self.state.set_value(True))
        if self._hvac_mode_raw(current_data) != hvac_mode:
            program_key = self._program_dict.inverse.get(hvac_mode)
            if program_key is None:
                raise Exception(f"Unrecognized fan mode {hvac_mode}")
            result.append(self.program.set_value(program_key))
        return result

    @property
    def options(self) -> list[HVACMode]:
        return [
            self._program_dict[program] for program in self.program.options.values()
        ] + [HVACMode.OFF]


class ClimateControl(Control):
    key = "ac"

    def __init__(
        self,
        hvac_mode: HvacControl,
        target_temperature: WriteNumericControl,
        current_temperature: NumericControl,
        fan_mode: WriteEnumControl,
        swing: SwingControl,
    ):
        self.hvac_mode = hvac_mode
        self.target_temperature = target_temperature
        self.current_temperature = current_temperature
        self.fan_mode = fan_mode
        self.swing = swing
        self._controls = [
            hvac_mode,
            target_temperature,
            current_temperature,
            fan_mode,
            swing,
        ]

    def get_value(self, data: bytearray) -> dict[str, Any]:
        return {c.key: c.get_value(data) for c in self._controls}


def get_bounded_values_options(
    key: str, values: ApplianceFeatureBoundedOption
) -> bidict[int, str]:
    result: bidict[int, str] = bidict()
    value = float(values.lowerLimit)
    while value <= values.upperLimit:
        wifiValue = int(value / values.factor)
        unit = unit_for_key(key)
        value_str = f"{value:g}"
        name = f"{value_str}{unit}" if unit is not None else value_str
        result[wifiValue] = to_friendly_name(name)
        value += values.step
    return result


def get_options_from_feature(key: str, feature: ApplianceFeature) -> bidict[int, str]:
    options: bidict[int, str] = bidict()
    if feature.enumValues is not None:
        for option in feature.enumValues:
            friendly_name = to_friendly_name(option.strKey)
            # Friendly names are not always unique
            if friendly_name in options.inverse:
                friendly_name = f"{friendly_name}_{option.wifiArrayValue}"
            options[option.wifiArrayValue] = friendly_name
    if feature.boundedValues is not None:
        for boundedValues in feature.boundedValues:
            options = (
                get_bounded_values_options(to_friendly_name(key), boundedValues)
                | options
            )
    return bidict(sorted(options.items()))


def get_options_from_enum_options(
    options: Sequence[ApplianceFeatureEnumOption],
) -> dict[int, str]:
    return {
        option.wifiArrayValue: to_friendly_name(option.strKey) for option in options
    }


def build_read_control_from_feature(feature: ApplianceFeature) -> Control | None:
    key = feature.strKey
    if key is None:
        return None
    key = to_friendly_name(key)
    if (
        feature.enumValues is None
        and feature.boundedValues is not None
        and len(feature.boundedValues) == 1
    ):
        return NumericControl(
            key=key,
            read_index=feature.wifiArrayIndex,
            bounds=feature.boundedValues[0],
        )
    return EnumControl(
        key=key,
        read_index=feature.wifiArrayIndex,
        options=get_options_from_feature(key, feature),
    )


def build_write_control_from_feature(feature: ApplianceFeature) -> Control | None:
    write_index = (
        feature.wfaWriteIndex
        if feature.wfaWriteIndex is not None
        else feature.wifiArrayIndex
    )
    key = feature.strKey
    if key is None:
        return None
    key = to_friendly_name(key)
    if (
        feature.enumValues is None
        and feature.boundedValues is not None
        and len(feature.boundedValues) == 1
    ):
        return WriteNumericControl(
            key=key,
            read_index=feature.wifiArrayIndex,
            write_index=write_index,
            bounds=feature.boundedValues[0],
        )
    return WriteEnumControl(
        key=key,
        read_index=feature.wifiArrayIndex,
        write_index=write_index,
        options=get_options_from_feature(key, feature),
    )


def build_control_from_program(program: ApplianceProgram) -> Control:
    return WriteEnumControl(
        key=to_friendly_name(program.strKey),
        read_index=program.wifiArrayIndex,
        write_index=(
            program.wfaWriteIndex
            if program.wfaWriteIndex is not None
            else program.wifiArrayIndex
        ),
        options=bidict(get_options_from_enum_options(program.values)),
    )


def build_control_from_substate(
    sub_states: ApplianceSubState | None,
) -> Control | None:
    if sub_states is None:
        return None
    return EnumControl(
        key="sub_state",
        read_index=sub_states.wifiArrayReadIndex,
        options=get_options_from_enum_options(sub_states.subStates),
    )


def build_controls_from_monitorings(
    monitorings: list[ApplianceFeature] | None,
) -> Iterable[Control | None]:
    if monitorings is None:
        return []
    return map(build_read_control_from_feature, monitorings)


def build_control_from_state(state: ApplianceState | None) -> Control | None:
    if state is None:
        return None
    read_index = state.wifiArrayReadIndex
    write_index = (
        state.wifiArrayWriteIndex
        if state.wifiArrayWriteIndex is not None
        else state.wfaIndex
    )
    if read_index is None or write_index is None:
        return None
    return WriteEnumControl(
        key="state",
        read_index=read_index,
        write_index=write_index,
        options=bidict(get_options_from_enum_options(state.states)),
    )


def build_controls_from_progress_variables(
    progress_variables: ApplianceProgress | None,
) -> list[Control]:
    if progress_variables is None:
        return []

    results: list[Control] = []
    # To keep track of keys for which a calculated control will be built
    delay_keys: dict[str, tuple[str, int]] = {}

    for field in fields(progress_variables):
        feature: ApplianceProgressFeature | None = getattr(
            progress_variables, field.name
        )
        if feature is not None:
            feature_key = to_friendly_name(feature.strKey)
            # Restrict this to washing machine only
            # Replaces washer_delay feature with SummedTimestampControl feature
            if feature.isCalculatedToStart is not None and feature_key in [
                "washer_delay"
            ]:
                calculation_key = feature_key
                feature_key = "delay_start#" + str(len(delay_keys))
                delay_keys.update(
                    {calculation_key: (feature_key, feature.isCalculatedToStart)}
                )
            results.append(
                TimeControl(
                    key=feature_key,
                    hour_index=feature.hour.wifiArrayIndex,
                    minute_index=feature.minute.wifiArrayIndex
                    if feature.minute is not None
                    else None,
                )
            )

    # Build calculated controls
    for calculation_key, feature_key_tuple in delay_keys.items():
        feature_key = feature_key_tuple[0]

        # Key for the new remaining time control
        remaining_key: str = "_".join(calculation_key.split("_")[:-1] + ["remaining"])
        _LOGGER.debug(
            "Detected time based calculated feature %s "
            "end time calculations will based on %s",
            calculation_key,
            remaining_key,
        )

        if feature_key_tuple[1] == 1:
            end_time_key = feature_key.replace("delay_start", "delay_end_time", 1)
            start_time_key = calculation_key
        else:
            end_time_key = calculation_key
            start_time_key = feature_key.replace("delay_start", "delay_start_time", 1)

        timestamp_sensors = {
            end_time_key: [
                control
                for control in results
                if control.key in [feature_key, remaining_key]
            ],
            start_time_key: [
                control for control in results if control.key in [feature_key]
            ],
        }

        # Calculations based on end_time need both feature_key and remaining_key
        if len(timestamp_sensors[end_time_key]) <= 1:
            del timestamp_sensors[end_time_key]
        # Remove sensor if no control is present
        if len(timestamp_sensors[start_time_key]) == 0:
            del timestamp_sensors[start_time_key]

        _LOGGER.debug("Adding sensor info %s:", timestamp_sensors.keys())

        results.extend(
            [
                SummedTimestampControl(key=name, sensors=sensors)
                for name, sensors in timestamp_sensors.items()
            ]
        )
    return results


def build_control_from_remote_control(
    remote_control: ApplianceRemoteControl | None,
) -> Control | None:
    if remote_control is None:
        return None
    return BooleanCompareControl(
        key="remote_control",
        read_index=remote_control.wifiArrayReadIndex,
        compare_value=remote_control.wifiArrayValue,
    )


def build_controls_from_warnings(warnings: ApplianceWarning | None) -> list[Control]:
    if warnings is None:
        return []

    return [
        BooleanBitmaskControl(
            key=to_friendly_name(warn.strKey),
            read_index=warnings.wifiArrayReadIndex,
            bit=warn.bitIndex,
        )
        for warn in warnings.warnings
    ]


def build_controls_from_features(
    settings: list[ApplianceFeature] | None,
) -> list[Control | None]:
    if settings is None:
        return []

    return [build_write_control_from_feature(s) for s in settings]


def convert_to_bool_control_if_possible(control: Control) -> Control:
    if not isinstance(control, WriteEnumControl):
        return control
    options = control.options.inverse
    option_keys = list(options.keys())
    option_keys.sort()
    if (
        len(option_keys) == 2
        and option_keys[0].endswith("_off")
        and option_keys[1].endswith("_on")
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
    if "air_conditioner_program" in keys:
        state = controls_dict["state"]
        assert isinstance(state, WriteBooleanControl)
        program = controls_dict["air_conditioner_program"]
        assert isinstance(program, WriteEnumControl)
        current_temperature = controls_dict["air_conditioner_room_temperature"]
        assert isinstance(current_temperature, NumericControl)
        target_temperature = controls_dict["air_conditioner_target_temperature"]
        assert isinstance(target_temperature, WriteNumericControl)
        fan_mode = controls_dict["air_conditioner_wind_strength"]
        assert isinstance(fan_mode, WriteEnumControl)
        vertical_swing_control = controls_dict.get(
            "air_conditioner_up_down_vane_control"
        )
        assert vertical_swing_control is None or isinstance(
            vertical_swing_control, (WriteEnumControl, WriteBooleanControl)
        )
        horizontal_swing_control = controls_dict.get(
            "air_conditioner_left_right_vane_control"
        )
        assert horizontal_swing_control is None or isinstance(
            horizontal_swing_control, WriteEnumControl
        )

        climate = ClimateControl(
            hvac_mode=HvacControl(program, state),
            current_temperature=current_temperature,
            target_temperature=target_temperature,
            fan_mode=fan_mode,
            swing=SwingControl(horizontal_swing_control, vertical_swing_control),
        )
        excluded_controls = [
            program,
            state,
            current_temperature,
            target_temperature,
            fan_mode,
        ]
        return [c for c in controls if c not in excluded_controls] + [climate]
    return controls


# Only generate controls once to allow basic inter-Control communication
# Use entry id as key to avoid issues when multiple homewhiz devices are used
controls: dict[str, list[Control]] = {}


def generate_controls_from_config(
    key: str,
    config: ApplianceConfiguration,
) -> list[Control]:
    global controls

    if key not in controls:
        possible_controls: list[Control | None] = [
            build_control_from_state(config.deviceStates),
            build_control_from_program(config.program),
            build_control_from_substate(config.deviceSubStates),
            *build_controls_from_features(config.subPrograms),
            *build_controls_from_features(config.customSubPrograms),
            *build_controls_from_monitorings(config.monitorings),
            *build_controls_from_progress_variables(config.progressVariables),
            build_control_from_remote_control(config.remoteControl),
            *build_controls_from_warnings(config.deviceWarnings),
            *build_controls_from_warnings(config.warnings),
            *build_controls_from_features(config.settings),
        ]

        tmp_controls = [
            convert_to_bool_control_if_possible(control)
            for control in possible_controls
            if control is not None
        ]
        controls[key] = extract_ac_control(tmp_controls)

    return controls[key]
