import unittest

from src.ast import *
from src.environment import Environment
from src.parser import Parser


class TestEvaluating(unittest.TestCase):
    def test_function_call(self):
        decl = FunctionDeclaration('add',
                                   [FunctionParameter('a', TypeId('int')), FunctionParameter('b', TypeId('int'))],
                                   TypeId('int'),
                                   Add(LValue('a', None, 0, 1), LValue('b', None, 0, 2)))
        call = FunctionCall('add', [IntegerValue(1), IntegerValue(1)])
        env = Environment()
        env.push(1)
        env.set((0, 0), decl)

        result = call.evaluate(env)

        self.assertEqual(IntegerValue(2), result)
        self.assertEqual(1, env.size())

    def test_native_function_call(self):
        decl = NativeFunctionDeclaration('square',
                                         [FunctionParameter('a', TypeId('int'))],
                                         TypeId('int'),
                                         lambda a: IntegerValue(a.integer * a.integer))
        call = FunctionCall('square', [IntegerValue(7)])
        env = Environment()
        env.push(1)
        env.set((0, 0), decl)

        result = call.evaluate(env)

        self.assertEqual(IntegerValue(49), result)
        self.assertEqual(1, env.size())

    def test_arrays(self):
        type = TypeId('int_array')
        length = Add(IntegerValue(1), IntegerValue(1))
        initial_value = Add(IntegerValue(2), IntegerValue(2))
        array_creation = ArrayCreation(type, length, initial_value)

        result = array_creation.evaluate(Environment())

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
        # [], [42], [x]...

        program = Parser(code).parse()
        env = Environment()
        env.push(1)
        env.set((0, 0), IntegerValue(42))

        # with 'a := 42', run the function to change the environment
        a = program.declarations[0].body.lvalue
        a.level, a.index = 2, 0
        program.evaluate(env)

        self.assertEqual(IntegerValue(99), env.get((0, 0)))

    def test_scoped_environment_still_affected_by_function_call(self):
        code = """
        let 
          function x() = a := 99
        in
          let 
            var a := 0
          in
            x()
          end
        end
        """
        program = Parser(code).parse()
        env = Environment()
        env.push(1)
        env.set((0, 0), IntegerValue(42))

        # with 'a := 42', run the function to change the environment and it should still affect the outer scope
        a1 = program.declarations[0].body.lvalue
        a1.level, a1.index = 2, 0

        program.evaluate(env)

        self.assertEqual(IntegerValue(99), env.get((0, 0)))


if __name__ == '__main__':
    unittest.main()
