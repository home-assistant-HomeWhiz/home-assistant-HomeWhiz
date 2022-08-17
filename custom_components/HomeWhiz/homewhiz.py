from dataclasses import dataclass
from enum import Enum
from typing import Optional

from bleak import BleakScanner


class DeviceState(Enum):
    ON = 10
    OFF = 20
    RUNNING = 30
    PAUSED = 40
    TIME_DELAY_ACTIVE = 60
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object):
        return cls.UNKNOWN


class DeviceSubState(Enum):
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
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object):
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


async def scan():
    devices = await BleakScanner.discover()
    return [d for d in devices if d.name.startswith("HwZ")]


class MessageAccumulator:
    expected_index = 0
    accumulated = []

    def accumulate_message(self, message: bytearray):
        message_index = message[4]
        if message_index == 0:
            self.accumulated = message[7:]
            self.expected_index = 1
        elif self.expected_index == 1:
            full_message = self.accumulated + message[7:]
            self.expected_index = 0
            return full_message


def parse_message(message: bytearray):
    return WasherState(
        device_state=DeviceState(message[35]),
        device_sub_state=DeviceSubState(message[50]),
        temperature=message[37],
        spin=message[38] * 100,
        rinse_hold=message[38] == 17,
        duration_minutes=message[44] * 60 + message[45],
        remaining_minutes=message[46] * 60 + message[47],
        delay_minutes=None if message[48] == 128 else message[48] * 60 + message[49]
    )
