import unittest

from src.ast import add_immutable_fields


class A:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c


class B:
    a = 42


class C:
    __init__ = 42


class TestRPythonizing(unittest.TestCase):
    def test_adding_immutable_fields(self):
        add_immutable_fields(A)
        self.assertListEqual(['a', 'b', 'c'], A._immutable_fields_)

    def test_no_init(self):
        add_immutable_fields(B)
        self.assertTrue(not hasattr(B, '_immutable_fields_'))

    def test_init_is_not_a_function(self):
        add_immutable_fields(C)
        self.assertTrue(not hasattr(C, '_immutable_fields_'))


if __name__ == '__main__':
    unittest.main()
