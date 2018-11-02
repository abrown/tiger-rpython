import unittest

from src.ast import *
from src.environment import Environment
from src.main.util import create_environment_with_natives, list_native_environment_names
from src.parser import Parser


class TestUtil(unittest.TestCase):
    def test_function_call(self):
        env = create_environment_with_natives()
        names = list_native_environment_names(env)

        self.assertListEqual(['print', 'timeGo', 'timeStop'], names)


if __name__ == '__main__':
    unittest.main()
