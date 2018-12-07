import sys

from src.native_functions import read_file, create_native_functions, create_empty_environment
from src.parser import Parser, ParseError


def main(argv):
    """Parse and run any Tiger program"""

    # check for arguments
    try:
        file = argv[1]
    except IndexError:
        print("Expected one file name argument to be passed, e.g. ./tiger-interpreter program.tig")
        return 40

    program_contents = read_file(argv[1])

    # set up environment
    environment = create_empty_environment()

    # parse input program
    try:
        program = Parser(program_contents, argv[1]).parse(create_native_functions())
    except ParseError as e:
        print("Parse failure: %s" % e.to_string())
        return 42

    # evaluate the program
    result = program.evaluate(environment)

    # print the result and exit
    if result:
        print(result.to_string())
    return 0


if __name__ == "__main__":
    code = main(sys.argv)
    sys.exit(code)


def target(*args):
    return main, None
