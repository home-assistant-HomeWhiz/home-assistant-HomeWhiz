# Base component constants
from homeassistant.const import Platform

NAME = "HomeWhiz"
DOMAIN = "homewhiz"
DOMAIN_DATA = f"{DOMAIN}_data"
PLATFORMS = [Platform.SELECT, Platform.SENSOR]
VERSION = "0.0.0"
CONF_TYPE = "type"
CONF_CLOUD = "could"
CONF_BLUETOOTH = "bt"
ISSUE_URL = "https://github.com/rowysock/home-assistant-HomeWhiz/issues"

# Icons
ICON = "mdi:washing-machine"

# Defaults
DEFAULT_NAME = DOMAIN
