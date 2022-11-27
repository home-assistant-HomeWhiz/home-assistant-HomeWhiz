import unittest

from custom_components.homewhiz import parse_message
from custom_components.homewhiz.homewhiz import DeviceState, DeviceSubState

on = bytearray.fromhex(
    "002f4a45a10100000000000000000000000000000000000000000200000000000000000a011e0c0000000080021102110000000000000000000000000000000100000000000001070000000000"
)
running = bytearray.fromhex(
    "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e0c0080000080021100398080010000000000000000000080808100800000008001078000808000"
)
spinning = bytearray.fromhex(
    "002f4a45a10100000000000000000000000000000000000000000200000000000000001e819e8c00808080800211000a8080020000000000000000008080808180800000008081078000808000"
)


class ParserTestCase(unittest.TestCase):
    def test_on(self):
        actual = parse_message(on)
        self.assertEqual(actual.device_state, DeviceState.ON)
        self.assertEqual(actual.temperature, 30)
        self.assertEqual(actual.spin, 1200)
        self.assertEqual(actual.rinse_hold, False)
        self.assertEqual(actual.duration_minutes, 137)
        self.assertEqual(actual.remaining_minutes, 137)
        self.assertEqual(actual.delay_minutes, 0)
        self.assertEqual(actual.device_sub_state, DeviceSubState.UNKNOWN)

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


if __name__ == "__main__":
    unittest.main()
