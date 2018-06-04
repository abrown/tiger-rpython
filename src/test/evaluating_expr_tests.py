import unittest

from src.test.util import parse_file, list_test_files, get_file_name


class TestEvaluatingExprTests(unittest.TestCase):
    pass


def generate_expression_test(path):
    def test(self):
        program = parse_file(path)
        result = program.evaluate()

        expected = parse_file(path.replace('.tig', '.out.bak'))

        self.assertEqual(expected, result)

    return test


# dynamically add each test in 'expr-tests' as a method of TestEvaluatingExprTests
for f in list_test_files('expr-tests'):
    name = 'test_' + get_file_name(f)
    test = generate_expression_test(f)
    setattr(TestEvaluatingExprTests, name, test)

if __name__ == '__main__':
    unittest.main()
