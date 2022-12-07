import logging

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


def get_brand_name(brand_index: int):
    match brand_index:
        case 2:
            return "Grundig"
        case 3:
            return "Beko"
        case 4:
            return "Blomberg"
        case 5:
            return "Elektrabregenz"
        case 6:
            return "Arctic"
        case 7:
            return "Defy"
        case 8:
            return "Leisure"
        case 9:
            return "Flavel"
        case 10:
            return "Altus"
        case 11:
            return "Dawlance"
        case 12:
            return "Viking"
        case 13:
            return "Cylinda"
        case 14:
            return "Smeg"
        case 15:
            return "V-Zug"
        case 16:
            return "Lamona"
        case 17:
            return "Teka"
        case 18:
            return "Voltas Beko"
        case _:
            return "Arcelik"
