import unittest

from src.ast import *
from src.environment import Environment
from src.parser import Parser
from test_utilities import OutputContainer


class TestEvaluating(unittest.TestCase):
    def evaluate(self, program, *existing_declarations):
        existing_declarations_ast = [Parser(decl).parse() if isinstance(decl, str) else decl for decl in
                                     existing_declarations]
        if not existing_declarations_ast:
            # ensure we have at least one existing declaration or the parser will not run the lvalue-transformation pass
            existing_declarations_ast.append(NativeNoArgumentFunctionDeclaration('unused', None, lambda: None))
        assert all(isinstance(a, Program) for a in existing_declarations_ast)
        assert isinstance(program, str)
        program_ast = Parser(program).parse(existing_declarations_ast)
        return program_ast.evaluate(Environment.empty())

    def test_function_call(self):
        result = self.evaluate("add(1, 1)", "function add(a:int, b:int):int = a + b")
        self.assertEqual(IntegerValue(2), result)

    def test_native_function_call(self):
        square_function = NativeOneArgumentFunctionDeclaration('square',
                                                               [FunctionParameter('a', TypeId('int'))],
                                                               TypeId('int'),
                                                               lambda a: IntegerValue(a.integer * a.integer))
        result = self.evaluate("square(7)", square_function)
        self.assertEqual(IntegerValue(49), result)

    def test_array_creation(self):
        type = TypeId('int_array')
        length = Add(IntegerValue(1), IntegerValue(1))
        initial_value = Add(IntegerValue(2), IntegerValue(2))
        array_creation = ArrayCreation(type, length, initial_value)

        result = array_creation.evaluate(Environment.empty())

        self.assertIsInstance(result, ArrayValue)
        self.assertEqual(2, result.length)
        self.assertEqual(2, len(result.array))
        self.assertEqual(IntegerValue(4), result.array[0])

    def test_environment_affected_by_function_call(self):
        code = """
        let 
          function x() = a := 99
        in
          x()
        end
        """

        # set 'a := 42' in a pre-existing environment
        decl = Let([VariableDeclaration(name='a', type=None, expression=IntegerValue(42))], [])

        # run the function to program the environment
        self.evaluate(code, decl)

        self.assertEqual(IntegerValue(99), decl.environment.get(0))

    def test_scoped_environment_still_affected_by_function_call(self):
        code = """
        let
          function x() = a := 99
        in
          let 
            var a := 0  // the difference between this test and the above is this re-assignment to 'a'
          in
            x()
          end
        end
        """

        # set 'a := 42' in a pre-existing environment
        decl = Let([VariableDeclaration(name='a', type=None, expression=IntegerValue(42))], [])

        # run the function to change the environment and it should still affect the outer scope
        self.evaluate(code, decl)

        self.assertEqual(IntegerValue(99), decl.environment.get(0))

    def test_for_loop(self):
        code = """
        for i := 1 to 9 do
            let var a := 42 in
                print(i)
            end
        """
        stdout = OutputContainer()
        print_function = NativeOneArgumentFunctionDeclaration('print', [FunctionParameter('string', TypeId('string'))],
                                                              None, stdout.capture)

        result = self.evaluate(code, print_function)

        self.assertEqual(None, result)
        self.assertEqual("123456789", stdout.get_captured())

    def test_function_recursion(self):
        code = """
        let
          function a(n:int) : int =
            if (n < 100) then
              a(n+1)
            else
              n
        in
          a(1)
        end
        """

        result = self.evaluate(code)

        self.assertEqual(IntegerValue(100), result)


if __name__ == '__main__':
    unittest.main()
