import os

from src.ast import IntegerValue, StringValue
from src.parser import Parser


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


def parse_file(path, native_function_names=None):
    contents = read_file(path)
    parser = Parser(contents, path)
    return parser.parse(native_function_names)


class OutputContainer:
    """Container for holding output"""
    __value__ = ""

    def capture(self, s):
        if isinstance(s, IntegerValue):
            self.__value__ += str(s.integer)
        elif isinstance(s, StringValue):
            self.__value__ += s.string
        else:
            raise ValueError('Unknown value type ' + str(s))

    def get_captured(self):
        return self.__value__
