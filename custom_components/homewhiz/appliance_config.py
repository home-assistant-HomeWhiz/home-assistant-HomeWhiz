from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ApplianceSubprogramOverride:
    allowedValueIndices: Optional[List[int]]
    isDisabled: Optional[int]
    strKeyRef: Optional[str]


@dataclass
class ApplianceProgressFeatureOverride:
    hour: ApplianceSubprogramOverride
    minute: Optional[ApplianceSubprogramOverride]
    strKeyRef: str


@dataclass
class ApplianceProgramOption:
    customSubProgramOverrides: Optional[List[ApplianceSubprogramOverride]]
    isDownloadableCycle: Optional[bool]
    progressVariableOverrides: Optional[List[ApplianceProgressFeatureOverride]]
    strKey: str
    subProgramOverrides: Optional[List[ApplianceSubprogramOverride]]
    wfaValue: Optional[int]
    isVisible: int = 1


@dataclass()
class ApplianceProgram:
    strKey: str
    isSwitch: Optional[int]
    values: List[ApplianceProgramOption]
    wifiArrayIndex: int
    wfaWriteIndex: Optional[int]
    isVisible: int = 1


@dataclass
class ApplianceFeatureBoundedOption:
    factor: float
    lowerLimit: int
    step: float
    strKey: str
    unit: str
    upperLimit: int


@dataclass
class ApplianceFeatureEnumOption:
    strKey: str
    wifiArrayValue: int


@dataclass
class ApplianceFeature:
    boundedValues: Optional[List[ApplianceFeatureBoundedOption]]
    enumValues: Optional[List[ApplianceFeatureEnumOption]]
    isSwitch: Optional[int]
    strKey: Optional[str]
    wifiArrayIndex: int
    wfaWriteIndex: Optional[int]
    isVisible: int = 1


@dataclass
class ApplianceProgressFeature:
    hour: ApplianceFeature
    isExpandableBySwitch: Optional[bool]
    minute: ApplianceFeature
    strKey: str
    wfaIndex: Optional[int]
    wfaWriteIndex: Optional[int]
    isCalculatedToStart: Optional[int]
    isVisible: int = 1


@dataclass
class ApplianceProgress:
    autoOff: Optional[ApplianceProgressFeature]
    autoOn: Optional[ApplianceProgressFeature]
    delay: ApplianceProgressFeature
    duration: ApplianceProgressFeature
    elapsed: Optional[ApplianceProgressFeature]
    fermentedremaining: Optional[ApplianceProgressFeature]
    remaining: Optional[ApplianceProgressFeature]
    remainingOrElapsed: Optional[ApplianceProgressFeature]


@dataclass
class ApplianceFeatureNotificationInfo:
    necessity: Optional[str]
    priority: str
    strKey: str


@dataclass
class ApplianceStateOption(ApplianceFeatureEnumOption):
    allowedTransitions: List[str]
    notificationInfo: ApplianceFeatureNotificationInfo


@dataclass
class ApplianceState:
    states: List[ApplianceStateOption]
    wfaIndex: Optional[int]
    wfaWriteIndex: Optional[int]
    wifiArrayReadIndex: Optional[int]


@dataclass
class ApplianceSubState:
    subStates: List[ApplianceFeatureEnumOption]
    wifiArrayReadIndex: int


@dataclass
class ApplianceConfiguration:
    program: ApplianceProgram
    subPrograms: List[ApplianceFeature]
    progressVariables: Optional[ApplianceProgress]
    deviceStates: Optional[ApplianceState]
    deviceSubStates: Optional[ApplianceSubState]
