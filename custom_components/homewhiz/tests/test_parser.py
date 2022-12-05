import unittest

from custom_components.homewhiz import parse_message
from custom_components.homewhiz.homewhiz import DeviceState, DeviceSubState

on = bytearray.fromhex(
    "002f4a45a10100000000000000000000000000000000000000000200000000000000000a011e0c"
    "0000000080021102110000000000000000000000000000000100000000000001070000000000"
)
running = bytearray.fromhex(
    "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c"
    "0080000080021100398080010000000000000000000080808100800000008001078000808000"
)
spinning = bytearray.fromhex(
    "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c"
    "00808080800211000a8080020000000000000000008080808180800000008081078000808000"
)

delay_defined = bytearray.fromhex(
    "003853e0ab0100000000000000000000000000000000000000000300000000000000000a01280e"
    "000000008002100210012c000000000000000000010000000100000000000001078000000000"
)

delay_started = bytearray.fromhex(
    "003853e0ab0100000000000000000000000000000000000000000300000000000000003c01280e"
    "00000000800210021081ac080000000000000000010000000100000000000001078000808000"
)


class TestParser(unittest.TestCase):
    def test_on(self):
        actual = parse_message(on)
        self.assertEqual(actual.device_state, DeviceState.ON)
        self.assertEqual(actual.temperature, 30)
        self.assertEqual(actual.spin, 1200)
        self.assertEqual(actual.rinse_hold, False)
        self.assertEqual(actual.duration_minutes, 137)
        self.assertEqual(actual.remaining_minutes, 137)
        self.assertEqual(actual.delay_minutes, 0)
        self.assertEqual(actual.device_sub_state, DeviceSubState.OFF)

    def test_running(self):
        actual = parse_message(running)
        self.assertEqual(actual.device_state, DeviceState.RUNNING)
        self.assertEqual(actual.temperature, 30)
        self.assertEqual(actual.spin, 1200)
        self.assertEqual(actual.rinse_hold, False)
        self.assertEqual(actual.duration_minutes, 137)
        self.assertEqual(actual.remaining_minutes, 57)
        self.assertEqual(actual.delay_minutes, None)
        self.assertEqual(actual.device_sub_state, DeviceSubState.WASHING)

    def test_spinning(self):
        actual = parse_message(spinning)
        self.assertEqual(actual.device_state, DeviceState.RUNNING)
        self.assertEqual(actual.temperature, 30)
        self.assertEqual(actual.spin, 1200)
        self.assertEqual(actual.rinse_hold, False)
        self.assertEqual(actual.duration_minutes, 137)
        self.assertEqual(actual.remaining_minutes, 10)
        self.assertEqual(actual.delay_minutes, None)
        self.assertEqual(actual.device_sub_state, DeviceSubState.SPIN)

    def test_delay_defined(self):
        actual = parse_message(delay_defined)
        self.assertEqual(actual.device_state, DeviceState.ON)
        self.assertEqual(actual.temperature, 40)
        self.assertEqual(actual.spin, 1400)
        self.assertEqual(actual.rinse_hold, False)
        self.assertEqual(actual.duration_minutes, 136)
        self.assertEqual(actual.remaining_minutes, 136)
        self.assertEqual(actual.delay_minutes, 104)
        self.assertEqual(actual.device_sub_state, DeviceSubState.OFF)

    def test_delay_started(self):
        actual = parse_message(delay_started)
        self.assertEqual(actual.device_state, DeviceState.TIME_DELAY_ACTIVE)
        self.assertEqual(actual.temperature, 40)
        self.assertEqual(actual.spin, 1400)
        self.assertEqual(actual.rinse_hold, False)
        self.assertEqual(actual.duration_minutes, 136)
        self.assertEqual(actual.remaining_minutes, 136)
        self.assertEqual(actual.delay_minutes, 104)
        self.assertEqual(actual.device_sub_state, DeviceSubState.TIME_DELAY_ENABLED)


if __name__ == "__main__":
    unittest.main()
