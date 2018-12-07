import sys
import unittest

from src.ast import FunctionParameter, TypeId, NativeOneArgumentFunctionDeclaration, Let, TypeDeclaration
from src.environment import Environment
from src.test.test_utilities import parse_file, list_test_files, get_file_name, read_file, OutputContainer

# note: this may be helpful for testing larger recursion depths
sys.setrecursionlimit(10000)


class TestEvaluatingPrintTests(unittest.TestCase):
    pass


def generate_print_test(path):
    def test(self):
        native_types = Let([TypeDeclaration('string', TypeId('string')), TypeDeclaration('int', TypeId('int'))], [])
        stdout = OutputContainer()
        capture_stdout_function = NativeOneArgumentFunctionDeclaration('print', [FunctionParameter('s', TypeId('str'))],
                                                                       None, stdout.capture)
        program = parse_file(path, [native_types, capture_stdout_function])
        env = Environment.empty()
        program.evaluate(env)

        expected = read_file(path.replace('.tig', '.out.bak'))
        self.assertEqual(expected, stdout.get_captured())

    return test


# dynamically add each test in 'print-tests' as a method of TestEvaluatingPrintTests
for f in list_test_files('print-tests'):
    name = 'test_' + get_file_name(f)
    test = generate_print_test(f)
    setattr(TestEvaluatingPrintTests, name, test)

if __name__ == '__main__':
    unittest.main()
