import sys

from src.native_functions import read_file
from src.parser import Parser, ParseError


def main(argv):
    """Parse and print any Tiger program"""

    # check for arguments
    try:
        file = argv[1]
    except IndexError:
        print("Expected one file name argument to be passed, e.g. ./tiger-parser program.tig")
        return 40

    program_contents = read_file(argv[1])

    # parse input program
    try:
        program = Parser(program_contents, argv[1]).parse()
    except ParseError as e:
        print("Parse failure: %s" % e.to_string())
        return 42

    # print the program
    print(program.to_string())

    return 0


if __name__ == "__main__":
    code = main(sys.argv)
    sys.exit(code)


def target(*args):
    return main, None
