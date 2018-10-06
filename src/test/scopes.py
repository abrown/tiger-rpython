import unittest

from src.ast import LValue, Let, FunctionDeclaration, FunctionCall, VariableDeclaration, \
    FunctionParameter, Add, IntegerValue, Declaration
from src.parser import Parser
from src.scopes import transform_lvalues, DepthFirstAstIterator, ExitScope


class TestScopeTransformations(unittest.TestCase):
    def to_program(self, text):
        program = Parser(text).parse()
        transform_lvalues(program)
        return program

    def ast_to_list(self, expression):
        return [node for node in DepthFirstAstIterator(expression)]

    def find_first_expression(self, root_expression, type):
        return next(self.find_all_expressions(root_expression, type))

    def find_all_expressions(self, root_expression, type):
        for exp in DepthFirstAstIterator(root_expression):
            if isinstance(exp, type):
                yield exp

    def assertLocationIs(self, lvalue, location):
        assert isinstance(lvalue, LValue)
        assert isinstance(location, tuple)

        self.assertEqual(location[0], lvalue.level,
                         'The level of LValue %s should be %d but is %d' % (lvalue.name, location[0], lvalue.level))
        self.assertEqual(location[1], lvalue.index,
                         'The index of LValue %s should be %d but is %d' % (lvalue.name, location[1], lvalue.index))

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
                                   Let, VariableDeclaration, IntegerValue, FunctionCall, LValue, ExitScope, ExitScope, ExitScope],
                                  nodes)

    def test_let(self):
        program = self.to_program("let var x := 42 in x + 42 end")
        x_used = self.find_first_expression(program, LValue)

        self.assertLocationIs(x_used, (0, 0))

    def test_let_nested(self):
        program = self.to_program("let var x := 42 in let var y := 43 in x + y end end")
        x_used = self.find_first_expression(program, LValue)

        self.assertLocationIs(x_used, (1, 0))

    def test_let_multiple(self):
        program = self.to_program("let var x := 42 var y := 43 in y + x end")
        y_used = self.find_first_expression(program, LValue)

        self.assertLocationIs(y_used, (0, 1))

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
        x_used = self.find_first_expression(program, LValue)

        self.assertLocationIs(x_used, (0, 1))  # the function name takes the first index slot

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
        y_used_first, y_used_second = self.find_all_expressions(program, LValue)

        self.assertLocationIs(y_used_first, (2, 0))  # y is from the first 'let' scope
        self.assertLocationIs(y_used_second, (0, 0))  # y is local to the third 'let y' scope

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
        x_used_first, x_used_second, x_used_third = self.find_all_expressions(program, LValue)

        self.assertLocationIs(x_used_first, (1, 0))
        self.assertLocationIs(x_used_second, (1, 0))
        self.assertLocationIs(x_used_third, (1, 0))

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

        self.assertEqual(l, LValue('l'))
        self.assertEqual(1, l.index)


if __name__ == '__main__':
    unittest.main()
