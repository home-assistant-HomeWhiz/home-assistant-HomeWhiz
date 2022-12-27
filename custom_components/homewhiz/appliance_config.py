from dataclasses import dataclass
from typing import Optional


@dataclass
class ApplianceSubprogramOverride:
    allowedValueIndices: Optional[list[int]]
    isDisabled: Optional[int]
    strKeyRef: Optional[str]


@dataclass
class ApplianceProgressFeatureOverride:
    hour: ApplianceSubprogramOverride
    minute: Optional[ApplianceSubprogramOverride]
    strKeyRef: str


@dataclass
class ApplianceFeatureEnumOption:
    strKey: str
    wifiArrayValue: int


@dataclass
class ApplianceProgramOption(ApplianceFeatureEnumOption):
    customSubProgramOverrides: Optional[list[ApplianceSubprogramOverride]]
    isDownloadableCycle: Optional[bool]
    progressVariableOverrides: Optional[list[ApplianceProgressFeatureOverride]]
    strKey: str
    subProgramOverrides: Optional[list[ApplianceSubprogramOverride]]
    wifiArrayValue: int
    isVisible: int = 1


@dataclass()
class ApplianceProgram:
    strKey: str
    isSwitch: Optional[int]
    values: list[ApplianceProgramOption]
    wifiArrayIndex: int
    wfaWriteIndex: Optional[int]
    isVisible: int = 1


@dataclass
class ApplianceFeatureBoundedOption:
    factor: float
    lowerLimit: int
    step: float
    strKey: str
    unit: Optional[str]
    upperLimit: int


@dataclass
class ApplianceFeature:
    boundedValues: Optional[list[ApplianceFeatureBoundedOption]]
    enumValues: Optional[list[ApplianceFeatureEnumOption]]
    isSwitch: Optional[int]
    strKey: Optional[str]
    wifiArrayIndex: int
    wfaWriteIndex: Optional[int]
    isVisible: int = 1


@dataclass
class ApplianceProgressFeature:
    hour: ApplianceFeature
    isExpandableBySwitch: Optional[int]
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
    delay: Optional[ApplianceProgressFeature]
    duration: Optional[ApplianceProgressFeature]
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
    allowedTransitions: list[str]
    notificationInfo: ApplianceFeatureNotificationInfo


@dataclass
class ApplianceState:
    states: list[ApplianceStateOption]
    wfaIndex: Optional[int]
    wifiArrayWriteIndex: Optional[int]
    wifiArrayReadIndex: Optional[int]


@dataclass
class ApplianceSubState:
    subStates: list[ApplianceFeatureEnumOption]
    wifiArrayReadIndex: int


@dataclass
class OvenMeatProbePlug:
    wifiArrayReadIndex: int
    wifiArrayValue: int


@dataclass
class ApplianceOvenMeatProbe:
    meatProbePrograms: list[str]
    meatProbeSubprograms: list[ApplianceFeature]
    meatProbePlug: OvenMeatProbePlug


@dataclass
class AutoController:
    hasAutoController: bool


@dataclass
class ConsumableWarningSetting:
    bitIndex: int
    wifiArrayReadIndex: int


@dataclass
class ConsumableForm:
    autoDosingAmountSetting: Optional[ApplianceFeature]
    consumableForm: str
    lastCycleConsumptionAmountDataArrayReadIndex: int
    warningSetting: Optional[ConsumableWarningSetting]


@dataclass
class Consumable:
    consumableType: str
    forms: list[ConsumableForm]


@dataclass
class ApplianceConsumableSettings:
    consumables: list[Consumable]


@dataclass
class ApplianceProgramDownloadSettings:
    strKey: str
    wifiArrayReadIndex: int


@dataclass
class ApplianceClock:
    hourWifiArrayIndex: int
    minuteWifiArrayIndex: int


@dataclass
class HobZoneRecipeInfo:
    readyMealCurrentStepReadIndex: int
    readyMealIdHighReadIndex: int
    readyMealIdLowReadIndex: int


@dataclass
class ApplianceWarningReason:
    values: list[ApplianceFeatureEnumOption]
    wifiArrayReadIndex: int


@dataclass
class ApplianceWarningOption:
    bitIndex: int
    notificationInfo: ApplianceFeatureNotificationInfo
    reasonInfo: Optional[ApplianceWarningReason]
    strKey: str


@dataclass
class ApplianceWarning:
    wifiArrayByteCount: Optional[int]
    warnings: list[ApplianceWarningOption]
    wifiArrayReadIndex: int


@dataclass
class HobDefaultZone:
    cookingStates: ApplianceState
    monitorings: ApplianceFeature
    program: ApplianceProgram
    progressVariables: ApplianceProgress
    zoneRecipeInfo: HobZoneRecipeInfo
    subPrograms: list[ApplianceFeature]
    subStates: ApplianceSubState
    deviceWarnings: ApplianceWarning


@dataclass
class ApplianceHobZones:
    defaultZone: HobDefaultZone
    eachZoneWifiArraySegmentLength: int
    firstZoneWifiArrayStartIndex: int
    numberOfZones: int


@dataclass
class AutoBakeDownloadedFood:
    downloadedAutobakeIdHighWifiArrayIndex: int
    downloadedAutobakeIdLowWifiArrayIndex: int


@dataclass
class ApplianceOvenRecipe:
    cookingTypeRecipeWifiArrayValue: int
    cookingTypeWifiArrayIndex: int
    isRecipeUIHidden: Optional[str]
    recipeCommandLength: int
    recipeCommandWifiArrayStartIndex: int
    recipeFormatVersion: Optional[str]
    cookingTypeRecipeFromOvenStartedWifiArrayValue: Optional[int]
    cookingTypeRecipeFromOvenWifiArrayValue: Optional[int]
    recipeIdHighWifiArrayIndex: int
    recipeIdLowWifiArrayIndex: int


@dataclass
class ApplianceFeatureReference:
    strKeyRef: str
    wifiArrayIndex: int


@dataclass
class ApplianceProgramReference:
    strKeyRef: str
    wifiArrayIndex: int


@dataclass
class ApplianceProgressFeatureReference:
    hour: ApplianceFeatureReference
    minute: ApplianceFeatureReference
    strKeyRef: str


@dataclass
class ApplianceProgressReference:
    delay: ApplianceProgressFeature
    duration: ApplianceProgressFeatureReference
    remaining: ApplianceProgressFeature


@dataclass
class ApplianceSubprogramReference:
    strKeyRef: str
    wifiArrayIndex: int


@dataclass
class OvenCookingStep:
    program: ApplianceProgramReference
    progressVariables: ApplianceProgressReference
    stepEnableStatusIndex: int
    subPrograms: list[ApplianceSubprogramReference]


@dataclass
class ApplianceOvenStepCooking:
    activeStepIndex: int
    cookingTypeManuelWifiArrayValue: int
    cookingTypeStepCookingWifiArrayValue: int
    cookingTypeWifiArrayIndex: int
    defaultCookingStep: OvenCookingStep
    eachStepWifiArraySegmentLength: int
    firstStepWifiArrayStartIndex: int
    numberOfSteps: int


@dataclass
class OvenTemperatureInfo:
    ovenTemperatureNotVisiblePrograms: str
    ovenTemperatureSubprograms: ApplianceFeature


@dataclass
class ApplianceRefrigeratorDayTime:
    hourWfaIndex: int
    minuteWfaIndex: int


@dataclass
class ApplianceDefrostDuration:
    intervalCalculationFactor: int
    intervalWfaIndex: int
    startHourWfaIndex: int
    startMinuteWfaIndex: int


@dataclass
class ApplianceRefrigeratorDefrost:
    dayTimeVariableIndices: ApplianceRefrigeratorDayTime
    defrostConfigWfaIndex: int
    defrostCountdownWfaIndex: int
    defrostDurationIntervals: list[ApplianceDefrostDuration]
    defrostSelectWfaIndex: int


@dataclass
class ApplianceRemoteControl:
    wifiArrayReadIndex: int
    wifiArrayValue: int


@dataclass
class ApplianceScreenSaver:
    ovenScreenSaverTimer: ApplianceFeature
    ovenStandByMode: ApplianceFeature
    ovenStandByTimer: ApplianceFeature


@dataclass
class ApplianceTeaMachineRecipe:
    recipeFormatVersion: str
    recipeIdWifiArrayIndex: int


@dataclass
class ApplianceConfiguration:
    program: ApplianceProgram
    subPrograms: list[ApplianceFeature]
    progressVariables: Optional[ApplianceProgress]
    deviceStates: Optional[ApplianceState]
    deviceSubStates: Optional[ApplianceSubState]
    ovenMeatProbeAccessory: Optional[ApplianceOvenMeatProbe]
    autoController: Optional[AutoController]
    commands: Optional[list[ApplianceFeature]]
    consumableSettings: Optional[ApplianceConsumableSettings]
    customSubPrograms: Optional[list[ApplianceFeature]]
    downloadCycleSettingsModel: Optional[ApplianceProgramDownloadSettings]
    clock: Optional[ApplianceClock]
    zones: Optional[ApplianceHobZones]
    monitorings: Optional[list[ApplianceFeature]]
    ovenClockWifiArrayIndexes: Optional[ApplianceClock]
    ovenDownloadedAutoBakeInformation: Optional[AutoBakeDownloadedFood]
    ovenRecipeInformation: Optional[ApplianceOvenRecipe]
    stepCooking: Optional[ApplianceOvenStepCooking]
    ovenTemperatureInfo: Optional[OvenTemperatureInfo]
    refrigeratorDefrostInformation: Optional[ApplianceRefrigeratorDefrost]
    remoteControl: Optional[ApplianceRemoteControl]
    screenSaver: Optional[ApplianceScreenSaver]
    settings: Optional[list[ApplianceFeature]]
    teaRecipeInformation: Optional[ApplianceTeaMachineRecipe]
    deviceWarningsExtra: Optional[ApplianceWarning]
    deviceWarnings: Optional[ApplianceWarning]
    warnings: Optional[ApplianceWarning]
