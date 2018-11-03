import unittest

from src.ast import IntegerValue
from src.native_functions import create_environment_with_natives, list_native_environment_names, tiger_start_timer, \
    tiger_stop_timer


class TestUtil(unittest.TestCase):
    def test_function_call(self):
        env = create_environment_with_natives()
        names = list_native_environment_names(env)

        self.assertListEqual(['print', 'timeGo', 'timeStop'], names)

    def test_timer_in_python(self):
        tiger_start_timer()

        for i in range(100):
            i += i

        ticks = tiger_stop_timer()

        self.assertIsInstance(ticks, IntegerValue)
        self.assertGreater(ticks.integer, 0)


if __name__ == '__main__':
    unittest.main()
