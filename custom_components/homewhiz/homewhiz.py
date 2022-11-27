import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from homeassistant.components import bluetooth

_LOGGER: logging.Logger = logging.getLogger(__package__)


class DeviceState(Enum):
    ON = 10
    OFF = 20
    RUNNING = 30
    PAUSED = 40
    TIME_DELAY_ACTIVE = 60
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object):
        _LOGGER.warning("Unknown DeviceState: %s", value)
        return cls.UNKNOWN


class DeviceSubState(Enum):
    OFF = 0
    WASHING = 1
    SPIN = 2
    WATER_INTAKE = 3
    PREWASH = 4
    RINSING = 5
    SOFTENER = 6
    PROGRAM_STARTED = 7
    TIME_DELAY_ENABLED = 8
    PAUSED = 9
    ANALYSING = 10
    DOOR_LOCKED = 11
    OPENING_DOOR = 12
    LOCKING_DOOR = 13
    REMOVE_LAUNDRY = 15
    RINSE_HOLD = 17
    ADD_LAUNDRY = 19
    REMOTE_ANTICREASE = 20
    DRYING = 21
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object):
        _LOGGER.warning("Unknown DeviceSubState: %s", value)
        return cls.UNKNOWN


@dataclass
class WasherState:
    device_state: DeviceState
    device_sub_state: DeviceSubState
    temperature: int
    spin: int
    rinse_hold: bool
    duration_minutes: int
    remaining_minutes: int
    delay_minutes: Optional[int]


class ScannerHelper:
    async def scan(self, hass):
        devices = await bluetooth.async_get_scanner(hass).discover()
        return [d for d in devices if d.name.startswith("HwZ")]


class MessageAccumulator:
    expected_index = 0
    accumulated = []

    def accumulate_message(self, message: bytearray):
        _LOGGER.debug("Message (bytearray): %s", message)
        message_index = message[4]
        if message_index == 0:
            self.accumulated = message[7:]
            self.expected_index = 1
        elif self.expected_index == 1:
            full_message = self.accumulated + message[7:]
            self.expected_index = 0
            return full_message
        return None


def clamp(value: int):
    return value if value < 128 else value - 128


def parse_message(message: bytearray):
    return WasherState(
        device_state=DeviceState(message[35]),
        device_sub_state=DeviceSubState(message[50]),
        temperature=clamp(message[37]),
        spin=clamp(message[38]) * 100,
        rinse_hold=clamp(message[38]) == 17,
        duration_minutes=message[44] * 60 + message[45],
        remaining_minutes=message[46] * 60 + message[47],
        delay_minutes=None if message[48] == 128 else message[48] * 60 + message[49],
    )
