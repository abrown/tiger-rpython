import os
import unittest

from src.parser import Parser


class TestInterpreting(unittest.TestCase):
    pass


def list_test_files(directory):
    if not os.path.isabs(directory):
        current_directory = os.path.dirname(os.path.realpath(__file__))
        directory = os.path.join(current_directory, directory)
    for file in os.listdir(directory):
        if file.endswith('.tig'):
            yield os.path.join(directory, file)


def get_file_name(path):
    return os.path.basename(path)


def read_file(path):
    with open(path, 'r') as file:
        return file.read()


def parse_file(path):
    contents = read_file(path)
    parser = Parser(contents, path)
    return parser.parse()


def generate_test(path):
    def test(self):
        program = parse_file(path)
        result = program.evaluate()

        expected = parse_file(path.replace('.tig', '.out.bak'))

        self.assertEqual(expected, result)

    return test


# dynamically add each test in 'expr-tests' as a method of TestInterpreting
for f in list_test_files('expr-tests'):
    name = 'test_' + get_file_name(f)
    test = generate_test(f)
    setattr(TestInterpreting, name, test)

if __name__ == '__main__':
    unittest.main()
