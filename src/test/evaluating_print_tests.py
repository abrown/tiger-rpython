import sys
import unittest

from src.ast import FunctionParameter, TypeId, IntegerValue, StringValue, \
    NativeOneArgumentFunctionDeclaration
from src.environment import Environment
from src.test.test_utilities import parse_file, list_test_files, get_file_name, read_file, OutputContainer

# note: this may be helpful for testing larger recursion depths
sys.setrecursionlimit(10000)


class TestEvaluatingPrintTests(unittest.TestCase):
    pass


def generate_print_test(path):
    def test(self):
        program = parse_file(path, ['print'])  # see addition of print below
        stdout = OutputContainer()

        def tiger_print(s):
            if isinstance(s, IntegerValue):
                stdout.value += str(s.integer)
            elif isinstance(s, StringValue):
                stdout.value += s.string
            else:
                raise ValueError('Unknown value type ' + str(s))

        env = Environment.empty().push(1)
        env.set((0, 0), NativeOneArgumentFunctionDeclaration('print', [FunctionParameter('s', TypeId('str'))], None,
                                                             tiger_print))

        program.evaluate(env)

        expected = read_file(path.replace('.tig', '.out.bak'))
        self.assertEqual(expected, stdout.value)

    return test


# dynamically add each test in 'print-tests' as a method of TestEvaluatingPrintTests
for f in list_test_files('print-tests'):
    name = 'test_' + get_file_name(f)
    test = generate_print_test(f)
    setattr(TestEvaluatingPrintTests, name, test)

if __name__ == '__main__':
    unittest.main()
