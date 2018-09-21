import unittest

from src.environment_with_paths import Environment


class TestBinding(unittest.TestCase):
    def setUp(self):
        self.sut = Environment()

    def test_simple_put_and_get(self):
        p = (0, 0)
        self.sut.push(1)
        self.sut.set(p, 42)
        self.assertEqual(42, self.sut.get(p))

    def test_simple_get_no_put(self):
        p = (0, 0)
        self.sut.push(1)
        self.assertEqual(None, self.sut.get(p))

    def test_put_multiple(self):
        p1 = (0, 0)
        p2 = (0, 1)
        p3 = (0, 2)
        self.sut.push(2)
        self.sut.set(p1, "...")
        self.sut.set(p2, 42)

        self.assertEqual(42, self.sut.get(p2))
        self.assertEqual("...", self.sut.get(p1))
        with self.assertRaises(AssertionError):
            self.assertEqual(None, self.sut.get(p3))

    def test_hiding(self):
        p1 = (0, 0)
        p2 = (1, 0)
        self.sut.push(1)
        self.sut.set(p1, 1)
        self.assertEqual(1, self.sut.get(p1))

        self.sut.push(1)
        self.sut.set(p1, 2)
        self.assertEqual(2, self.sut.get(p1))
        self.assertEqual(1, self.sut.get(p2))
        self.sut.pop()

        self.assertEqual(1, self.sut.get(p1))

        with self.assertRaises(EnvironmentError):
            self.assertEqual(None, self.sut.get(p2))


if __name__ == '__main__':
    unittest.main()
