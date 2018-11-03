import unittest

from src.environments.environment_with_dictionary_tree import Environment


class TestBinding(unittest.TestCase):
    def setUp(self):
        self.sut = Environment()

    def test_simple_put_and_get(self):
        self.sut.push(1)
        self.sut.set('a', 42)
        self.assertEqual(42, self.sut.get('a'))

    def test_simple_get_no_put(self):
        self.assertEqual(None, self.sut.get('b'))

    def test_put_multiple(self):
        self.sut.push(2)
        self.sut.set('c', "...")
        self.sut.set('a', 42)

        self.assertEqual(42, self.sut.get('a'))
        self.assertEqual(None, self.sut.get('b'))
        self.assertEqual("...", self.sut.get('c'))

    def test_hiding(self):
        self.sut.push(1)
        self.sut.set('a', 1)
        self.sut.push(1)

        self.assertEqual(1, self.sut.get('a'))
        self.sut.set_current_level('a', 2)
        self.assertEqual(2, self.sut.get('a'))

        self.sut.pop()
        self.assertEqual(1, self.sut.get('a'))


if __name__ == '__main__':
    unittest.main()
