import unittest
from _ast import Break

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

    def test_negative_integer(self):
        self.assertParsesTo('-42', IntegerValue(-42))

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

    def test_assignment(self):
        self.assertParsesTo('a[0] := c()',
                            Assign(LValue('a', ArrayLValue(IntegerValue(0))), FunctionCall('c', [])))

    def test_if(self):
        self.assertParsesTo('if a() then b', If(FunctionCall('a', []), LValue('b')))

    def test_while(self):
        self.assertParsesTo('while true do b[i] := 0',
                            While(LValue('true'), Assign(LValue('b', ArrayLValue(LValue('i'))), IntegerValue(0))))

    def test_for(self):
        self.assertParsesTo('for a := 0 to 10 do x()',
                            For('a', IntegerValue(0), IntegerValue(10), FunctionCall('x', [])))

    def test_break(self):
        self.assertParsesTo('break', Break())

    def test_variable_declaration(self):
        self.assertParsesTo('var a := 42', VariableDeclaration('a', None, IntegerValue(42)))

    def test_variable_declaration_with_type(self):
        self.assertParsesTo('var a:int := 42', VariableDeclaration('a', TypeId('int'), IntegerValue(42)))

    def test_empty_function_declaration(self):
        self.assertParsesTo('function x() = noop', FunctionDeclaration('x', {}, None, LValue('noop')))

    def test_function_declaration(self):
        self.assertParsesTo('function x(y:int, z:int):int = add(y, z)',
                            FunctionDeclaration('x', {'y': TypeId('int'), 'z': TypeId('int')}, TypeId('int'),
                                                FunctionCall('add', [LValue('y'), LValue('z')])))

    def test_type_declaration(self):
        self.assertParsesTo('type x = int', TypeDeclaration('x', TypeId('int')))

    def test_type_declaration_with_record(self):
        self.assertParsesTo('type tree = {key: int, children: treelist}',
                            TypeDeclaration('tree', RecordType({'key': TypeId('int'), 'children': TypeId('treelist')})))

    def test_type_declaration_with_array(self):
        self.assertParsesTo('type treelist = array of tree', TypeDeclaration('treelist', ArrayType('tree')))

    def test_empty_sequence(self):
        self.assertParsesTo('()', Sequence([]))

    def test_single_item_sequence(self):
        self.assertParsesTo('(42)', Sequence([IntegerValue(42)]))

    def test_multiple_item_sequence(self):
        self.assertParsesTo('(a := 1; b := 2)',
                            Sequence([Assign(LValue('a'), IntegerValue(1)), Assign(LValue('b'), IntegerValue(2))]))

    def test_add_operator(self):
        self.assertParsesTo('a + b', Add(LValue('a'), LValue('b')))

    def test_multiply_operator(self):
        self.assertParsesTo('(a + b) * c', Multiply(Sequence([Add(LValue('a'), LValue('b'))]), LValue('c')))

    def test_multiply_operator_precedence(self):
        self.assertParsesTo('a + b * c', Add(LValue('a'), Multiply(LValue('b'), LValue('c'))))

    def test_simple_boolean_expression(self):
        self.assertParsesTo('a + b & c', And(Add(LValue('a'), LValue('b')), LValue('c')))

    def test_complex_boolean_expression(self):
        self.assertParsesTo('a + b > 42 | c < 42', Or(GreaterThan(Add(LValue('a'), LValue('b')), IntegerValue(42)),
                                                      LessThan(LValue('c'), IntegerValue(42))))

    def test_let_declarations(self):
        self.assertParsesTo('let var a := 1 var b := 2 in print(a) end',
                            Let([VariableDeclaration('a', None, IntegerValue(1)),
                                 VariableDeclaration('b', None, IntegerValue(2))],
                                [FunctionCall('print', [LValue('a')])]))

    def test_let_empty_declaration(self):
        self.assertParsesTo('let in x() end', Let([], [FunctionCall('x', [])]))

    def test_let_empty_body(self):
        self.assertParsesTo('let type x = int in end', Let([TypeDeclaration('x', TypeId('int'))], []))

    def test_let_multiple_expressions(self):
        self.assertParsesTo('let var x := 1 in y(); z() end', Let([VariableDeclaration('x', None, IntegerValue(1))],
                                                                  [FunctionCall('y', []), FunctionCall('z', [])]))


if __name__ == '__main__':
    unittest.main()
