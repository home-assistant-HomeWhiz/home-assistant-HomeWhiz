from dataclasses import dataclass


@dataclass
class ApplianceSubprogramOverride:
    allowedValueIndices: list[int] | None
    isDisabled: int | None
    strKeyRef: str | None


@dataclass
class ApplianceProgressFeatureOverride:
    hour: ApplianceSubprogramOverride
    minute: ApplianceSubprogramOverride | None
    strKeyRef: str


@dataclass
class ApplianceFeatureEnumOption:
    strKey: str
    wifiArrayValue: int


@dataclass
class ApplianceProgramOption(ApplianceFeatureEnumOption):
    customSubProgramOverrides: list[ApplianceSubprogramOverride] | None
    isDownloadableCycle: bool | None
    progressVariableOverrides: list[ApplianceProgressFeatureOverride] | None
    strKey: str
    subProgramOverrides: list[ApplianceSubprogramOverride] | None
    wifiArrayValue: int
    isVisible: int = 1


@dataclass()
class ApplianceProgram:
    strKey: str
    isSwitch: int | None
    values: list[ApplianceProgramOption]
    wifiArrayIndex: int
    wfaWriteIndex: int | None
    isVisible: int = 1


@dataclass
class ApplianceFeatureBoundedOption:
    factor: float
    lowerLimit: int
    step: float
    strKey: str
    unit: str | None
    upperLimit: int


@dataclass
class ApplianceFeature:
    boundedValues: list[ApplianceFeatureBoundedOption] | None
    enumValues: list[ApplianceFeatureEnumOption] | None
    isSwitch: int | None
    strKey: str | None
    wifiArrayIndex: int
    wfaWriteIndex: int | None
    isVisible: int = 1


@dataclass
class ApplianceProgressFeature:
    hour: ApplianceFeature
    isExpandableBySwitch: int | None
    minute: ApplianceFeature
    strKey: str
    wfaIndex: int | None
    wfaWriteIndex: int | None
    isCalculatedToStart: int | None
    isVisible: int = 1


@dataclass
class ApplianceProgress:
    autoOff: ApplianceProgressFeature | None
    autoOn: ApplianceProgressFeature | None
    delay: ApplianceProgressFeature | None
    duration: ApplianceProgressFeature | None
    elapsed: ApplianceProgressFeature | None
    fermentedremaining: ApplianceProgressFeature | None
    remaining: ApplianceProgressFeature | None
    remainingOrElapsed: ApplianceProgressFeature | None


@dataclass
class ApplianceFeatureNotificationInfo:
    necessity: str | None
    priority: str
    strKey: str


@dataclass
class ApplianceStateOption(ApplianceFeatureEnumOption):
    allowedTransitions: list[str]
    notificationInfo: ApplianceFeatureNotificationInfo


@dataclass
class ApplianceState:
    states: list[ApplianceStateOption]
    wfaIndex: int | None
    wifiArrayWriteIndex: int | None
    wifiArrayReadIndex: int | None


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
    autoDosingAmountSetting: ApplianceFeature | None
    consumableForm: str
    lastCycleConsumptionAmountDataArrayReadIndex: int
    warningSetting: ConsumableWarningSetting | None


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
    reasonInfo: ApplianceWarningReason | None
    strKey: str


@dataclass
class ApplianceWarning:
    wifiArrayByteCount: int | None
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
    isRecipeUIHidden: str | None
    recipeCommandLength: int
    recipeCommandWifiArrayStartIndex: int
    recipeFormatVersion: str | None
    cookingTypeRecipeFromOvenStartedWifiArrayValue: int | None
    cookingTypeRecipeFromOvenWifiArrayValue: int | None
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
    progressVariables: ApplianceProgress | None
    deviceStates: ApplianceState | None
    deviceSubStates: ApplianceSubState | None
    ovenMeatProbeAccessory: ApplianceOvenMeatProbe | None
    autoController: AutoController | None
    commands: list[ApplianceFeature] | None
    consumableSettings: ApplianceConsumableSettings | None
    customSubPrograms: list[ApplianceFeature] | None
    downloadCycleSettingsModel: ApplianceProgramDownloadSettings | None
    clock: ApplianceClock | None
    zones: ApplianceHobZones | None
    monitorings: list[ApplianceFeature] | None
    ovenClockWifiArrayIndexes: ApplianceClock | None
    ovenDownloadedAutoBakeInformation: AutoBakeDownloadedFood | None
    ovenRecipeInformation: ApplianceOvenRecipe | None
    stepCooking: ApplianceOvenStepCooking | None
    ovenTemperatureInfo: OvenTemperatureInfo | None
    refrigeratorDefrostInformation: ApplianceRefrigeratorDefrost | None
    remoteControl: ApplianceRemoteControl | None
    screenSaver: ApplianceScreenSaver | None
    settings: list[ApplianceFeature] | None
    teaRecipeInformation: ApplianceTeaMachineRecipe | None
    deviceWarningsExtra: ApplianceWarning | None
    deviceWarnings: ApplianceWarning | None
    warnings: ApplianceWarning | None
