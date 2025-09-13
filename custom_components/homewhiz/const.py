# Base component constants
from homeassistant.const import Platform

DOMAIN = "homewhiz"
PLATFORMS = [
    Platform.SELECT,
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]

# Configuration
CONF_BT_RECONNECT_INTERVAL = "bt_reconnect_interval"
CONF_TARGET_TEMPERATURE_LOW_OVERRIDE = "target_temperature_low_override"
CONF_TARGET_TEMPERATURE_HIGH_OVERRIDE = "target_temperature_high_override"
