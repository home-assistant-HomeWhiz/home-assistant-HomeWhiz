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
