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


if __name__ == '__main__':
    unittest.main()
