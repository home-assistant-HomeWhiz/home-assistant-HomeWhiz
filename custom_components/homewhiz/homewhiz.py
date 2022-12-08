import logging
from collections import defaultdict

_LOGGER: logging.Logger = logging.getLogger(__package__)


class MessageAccumulator:
    expected_index = 0
    accumulated = []

    def accumulate_message(self, message: bytearray):
        message_index = message[4]
        _LOGGER.debug("Message index: %d", message_index)
        if message_index == 0:
            self.accumulated = message[7:]
            self.expected_index = 1
        elif self.expected_index == 1:
            full_message = self.accumulated + message[7:]
            self.expected_index = 0
            return full_message
        return None


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
    },
)
