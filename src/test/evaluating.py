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


if __name__ == '__main__':
    unittest.main()
