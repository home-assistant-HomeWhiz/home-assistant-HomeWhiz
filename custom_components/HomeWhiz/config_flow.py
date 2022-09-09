from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from . import DOMAIN
from .homewhiz import ScannerHelper


async def _async_has_devices(hass: HomeAssistant) -> bool:
    scanner = ScannerHelper()
    devices = await scanner.scan(hass)
    return len(devices) > 0


config_entry_flow.register_discovery_flow(DOMAIN, "HomeWhiz", _async_has_devices)
