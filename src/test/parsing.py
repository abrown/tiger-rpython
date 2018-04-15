import unittest

from src.ast import TypeId
from src.parser import *


class TestParsing(unittest.TestCase):
    def assertParsesTo(self, text, expected_ast):
        sut = Parser(text)
        actual_ast = sut.parse()
        self.assertEqual(expected_ast, actual_ast)

    def test_nil(self):
        self.assertParsesTo('nil', NilValue())

    def test_integer(self):
        self.assertParsesTo('42', IntegerValue(42))

    def test_string(self):
        self.assertParsesTo('"abc"', StringValue('abc'))

    def test_array_creation(self):
        self.assertParsesTo('int[10] of 0', ArrayCreation(TypeId('int'), IntegerValue(10), IntegerValue(0)))

    def test_record_creation(self):
        self.assertParsesTo('A{b = 42, c = d}', RecordCreation(TypeId('A'), {'b': IntegerValue(42), 'c': LValue('d')}))

if __name__ == '__main__':
    unittest.main()
