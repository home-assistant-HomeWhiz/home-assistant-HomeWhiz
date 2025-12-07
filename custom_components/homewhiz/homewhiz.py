import abc
import logging
from abc import ABC
from collections import defaultdict
from dataclasses import dataclass

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass
class Command:
    index: int
    value: int


class HomewhizCoordinator(
    ABC,
    DataUpdateCoordinator[bytearray | None],  # type: ignore[type-arg]
):
    @abc.abstractmethod
    async def connect(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        pass

    @abc.abstractmethod
    async def send_command(self, command: Command) -> None:
        pass


brand_name_by_code = defaultdict(
    lambda: "Arcelik",
    {
        2: "Grundig",
        3: "Beko",
        4: "Blomberg",
        5: "Elektrabregenz",
        6: "Arctic",
        7: "Defy",
        8: "Leisure",
        9: "Flavel",
        10: "Altus",
        11: "Dawlance",
        12: "Viking",
        13: "Cylinda",
        14: "Smeg",
        15: "V-Zug",
        16: "Lamona",
        17: "Teka",
        18: "Voltas Beko",
        36: "Whirlpool",
        39: "Bauknecht",
    },
)

appliance_type_by_code = defaultdict(
    lambda: "None",
    {
        0: "NONE",
        1: "WASHER",
        2: "REFRIGERATOR",
        3: "DISHWASHER",
        4: "OVEN",
        5: "DRYER",
        6: "HERBGARDEN",
        7: "HOB",
        8: "HOOD",
        9: "AIR_CONDITIONER",
        10: "GATEWAY",
        11: "BOILER_CONTROLLER",
        12: "MOTION_SENSOR",
        13: "DOOR_SENSOR",
        14: "SMART_BUTTON",
        15: "TEMPERATURE_HUMIDITY_SENSOR",
        16: "LIGHT_BULB",
        17: "IR_BLASTER",
        18: "SMART_PLUG",
        19: "IP_CAMERA",
        20: "SMART_SWITCH",
        21: "RADIATOR_VALVE",
        22: "SMOKE_DETECTOR",
        23: "WATER_LEAK_SENSOR",
        24: "AIR_PURIFIER",
        25: "VACUUM_CLEANER",
        26: "CARBON_DIOXIDE_SENSOR",
        27: "TEA_MACHINE",
        28: "MULTIPLE_MESH",
        29: "YOGURT_MACHINE",
        30: "DRYANDWASHER",
        31: "TEA_COFFEE_MACHINE",
    },
)
