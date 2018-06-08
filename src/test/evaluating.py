import unittest

from src.ast import *
from src.environment import Environment


class TestEvaluating(unittest.TestCase):
    def test_function_call(self):
        decl = FunctionDeclaration('add',
                                   [FunctionParameter('a', TypeId('int')), FunctionParameter('b', TypeId('int'))],
                                   TypeId('int'),
                                   Add(LValue('a'), LValue('b')))
        call = FunctionCall('add', [IntegerValue(1), IntegerValue(1)])
        env = Environment()
        env.set(decl.name, decl)

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
        env.set(decl.name, decl)

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


if __name__ == '__main__':
    unittest.main()
