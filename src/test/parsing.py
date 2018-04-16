import unittest

from src.parser import *


class TestParsing(unittest.TestCase):
    def assertParsesTo(self, text, expected_ast):
        sut = Parser(text)
        actual_ast = sut.parse()
        self.assertEqual(expected_ast, actual_ast)

    def assertParseFails(self, text):
        with self.assertRaises(Exception) as context:
            sut = Parser(text)
            sut.parse()
        self.assertIsInstance(context.exception, ParseError)

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

    def test_object_creation(self):
        self.assertParsesTo('new X', ObjectCreation(TypeId('X')))

    def test_lvalue_plain(self):
        self.assertParsesTo('x', LValue('x'))

    def test_lvalue_record_access(self):
        self.assertParsesTo('x.y', LValue('x', RecordLValue('y')))

    def test_lvalue_array_access(self):
        self.assertParsesTo('x.y[z]', LValue('x', RecordLValue('y', ArrayLValue(LValue('z')))))

    def test_lvalue_computed_array_access(self):
        self.assertParsesTo('x[y()]', LValue('x', ArrayLValue(FunctionCall('y', []))))

    def test_lvalue_array_access_different_order(self):
        self.assertParsesTo('x[z].y', LValue('x', ArrayLValue(LValue('z'), RecordLValue('y'))))

    @unittest.skip("not ready yet")
    def test_spurious_lvalue(self):
        self.assertParseFails('x x')

    def test_function_call_without_arguments(self):
        self.assertParsesTo('a()', FunctionCall('a', []))

    def test_function_call_with_arguments(self):
        self.assertParsesTo('a(b, "c")', FunctionCall('a', [LValue('b'), StringValue('c')]))

    def test_method_call(self):
        self.assertParsesTo('a.b(42)', MethodCall(LValue('a'), 'b', [IntegerValue(42)]))

    def test_method_call_on_record(self):
        self.assertParsesTo('a.b.c(42)', MethodCall(LValue('a', RecordLValue('b')), 'c', [IntegerValue(42)]))

    def test_method_call_on_array(self):
        self.assertParsesTo('a[b].c()', MethodCall(LValue('a', ArrayLValue(LValue('b'))), 'c', []))


if __name__ == '__main__':
    unittest.main()
