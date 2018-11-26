import unittest

from src.ast import LValue, Let, FunctionDeclaration, FunctionCall, VariableDeclaration, \
    FunctionParameter, Add, IntegerValue, Declaration, Assign, RecordCreation, StringValue, RecordLValue, ArrayLValue, \
    TypeId, NativeOneArgumentFunctionDeclaration
from src.parser import Parser
from src.scopes import DepthFirstAstIterator, ExitScope


class TestScopeTransformations(unittest.TestCase):
    def to_program(self, text, absolutize_lvalues=True):
        print_declaration = NativeOneArgumentFunctionDeclaration('print', [FunctionParameter('message', TypeId('str'))],
                                                                 TypeId('nil'), lambda s: None)
        program = Parser(text).parse([print_declaration] if absolutize_lvalues else None)
        return program

    def ast_to_list(self, expression):
        return [node for node in DepthFirstAstIterator(expression)]

    def find_first_expression(self, root_expression, type):
        return next(self.find_all_expressions(root_expression, type))

    def find_all_expressions(self, root_expression, type):
        for exp in DepthFirstAstIterator(root_expression):
            if isinstance(exp, type):
                yield exp

    def assertBoundTo(self, lvalue, declaration):
        assert isinstance(lvalue, LValue)
        assert isinstance(declaration, Declaration)

        self.assertEqual(declaration, lvalue.declaration, 'LValue %s should be bound to %s but is bound to %s' % (
            lvalue.name, declaration, lvalue.declaration))
        self.assertEqual(declaration.name, lvalue.name,
                         'LValue %s should be have the same name as declaration %s but does not: %s != %s' % (
                             lvalue, declaration, lvalue.name, declaration.name))

    def assertListTypesEqual(self, type_list, instance_list):
        self.assertEqual(len(type_list), len(instance_list))
        for type, instance in zip(type_list, instance_list):
            self.assertIsInstance(instance, type)

    def test_iteration(self):
        program = self.to_program("let var x := 42 in x + 42 end")
        nodes = self.ast_to_list(program)

        self.assertListTypesEqual([Let, VariableDeclaration, IntegerValue, Add, LValue, IntegerValue, ExitScope], nodes)

    def test_more_complex_iteration(self):
        program = self.to_program(
            "let var y := 42 in let function f(x : int) = y + x in let var y := 43 in f(y) end end end")
        nodes = self.ast_to_list(program)

        self.assertListTypesEqual([Let, VariableDeclaration, IntegerValue,
                                   Let, FunctionDeclaration, FunctionParameter, Add, LValue, LValue, ExitScope,
                                   Let, VariableDeclaration, IntegerValue, FunctionCall, LValue, ExitScope, ExitScope,
                                   ExitScope],
                                  nodes)

    def test_record_iteration(self):
        program = self.to_program('r := rt {a = 42, b = "..."}', False)
        nodes = self.ast_to_list(program)

        self.assertListTypesEqual([Assign, LValue, RecordCreation, TypeId, IntegerValue, StringValue], nodes)

    def test_lvalue_iteration(self):
        program = self.to_program('a[b].c', False)
        nodes = self.ast_to_list(program)

        self.assertListTypesEqual([LValue, ArrayLValue, LValue, RecordLValue], nodes)

    def test_let(self):
        program = self.to_program("let var x := 42 in x + 42 end")
        x_declared = self.find_first_expression(program, VariableDeclaration)
        x_used = self.find_first_expression(program, LValue)

        self.assertBoundTo(x_used, x_declared)

    def test_let_nested(self):
        program = self.to_program("let var x := 42 in let var y := 43 in x + y end end")
        x_declared, y_declared = self.find_all_expressions(program, VariableDeclaration)
        x_used, y_used = self.find_all_expressions(program, LValue)

        self.assertBoundTo(x_used, x_declared)
        self.assertBoundTo(y_used, y_declared)

    def test_let_multiple(self):
        program = self.to_program("let var x := 42 var y := 43 in y + x end")
        x_declared, y_declared = self.find_all_expressions(program, VariableDeclaration)
        y_used = self.find_first_expression(program, LValue)

        self.assertBoundTo(y_used, y_declared)

    def test_let_in_function_call(self):
        program = self.to_program("""
        let 
            function print() = nil
            function f(x : int) = print(x) 
        in 
            let 
                var y := 43 
            in 
                f(y)
                end
        end
        """)
        print_declared, f_declared, x_declared, _ = self.find_all_expressions(program, Declaration)
        x_used = self.find_first_expression(program, LValue)

        self.assertBoundTo(x_used, x_declared)

    def test_let_redefined_outside_function_call(self):
        program = self.to_program("""
        let 
            var y := 42
        in 
            let 
                function f(x : int) = print(y) 
            in 
                let 
                    var y := 43 
                in 
                    f(y)
                end
            end
        end
        """)
        y_declared, f_declared, x_declared, y_declared_again = self.find_all_expressions(program, Declaration)
        y_used_first, y_used_second = self.find_all_expressions(program, LValue)

        self.assertBoundTo(y_used_first, y_declared)  # y is from the first 'let' scope
        self.assertBoundTo(y_used_second, y_declared_again)  # y is local to the third 'let y' scope

    def test_leaving_let(self):
        program = self.to_program("""
        let 
            var x := 42 
            function print() = nil
        in 
            (let var y := 42 in print(x) end;
            let var y := 42 in print(x) end;
            let var y := 42 in print(x) end)
        end
        """)
        x_declared = self.find_first_expression(program, VariableDeclaration)
        x_used_first, x_used_second, x_used_third = self.find_all_expressions(program, LValue)

        self.assertBoundTo(x_used_first, x_declared)
        self.assertBoundTo(x_used_second, x_declared)
        self.assertBoundTo(x_used_third, x_declared)

    def test_indexing_of_let_bindings(self):
        program = self.to_program("""
        let 
            var x := 42 
            function y() = nil
            var z := 99
        in 
            nil
        end
        """)
        x, y, z = self.find_all_expressions(program, Declaration)

        self.assertEqual(0, x.index)
        self.assertEqual(1, y.index)
        self.assertEqual(2, z.index)

    def test_array_creation(self):
        program = self.to_program("""
        let
          type iarray = array of int
          var x := 42
          var l := 3
          var a := iarray [l] of 0
        in
          42
        end
        """)

        l = next(self.find_all_expressions(program, LValue))
        _, _, l_declared, _ = self.find_all_expressions(program, Declaration)

        self.assertEqual(l, LValue('l'))
        self.assertBoundTo(l, l_declared)

    def test_for_loop(self):
        program = self.to_program("""
        for a := 1 to 9 do
          let var b := 42 in
            print(a)
           end
        """)

        p = self.find_first_expression(program, FunctionCall)
        a_declared = self.find_first_expression(program, VariableDeclaration)
        _, a, _, _ = self.find_all_expressions(program, LValue)

        self.assertBoundTo(a, a_declared)
        self.assertEqual('print', p.declaration.name)


if __name__ == '__main__':
    unittest.main()
