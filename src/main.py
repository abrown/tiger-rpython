import os
import sys

from src.parser import Parser, ParseError

# Begin RPython setup; catch import errors so this can still run in CPython...
try:
    from rpython.rlib.jit import JitDriver, elidable, promote, unroll_safe, jit_debug, we_are_jitted
except ImportError:
    class JitDriver(object):
        def __init__(self, **kw): pass

        def jit_merge_point(self, **kw): pass

        def can_enter_jit(self, **kw): pass

    def elidable(func):
        return func

    def promote(x):
        return x

    def unroll_safe(func):
        return func

    def jit_debug(string, arg1=0, arg2=0, arg3=0, arg4=0):
        pass

    def we_are_jitted():
        return False


def get_location(code):
    return "%s" % code


jitdriver = JitDriver(greens=['code'], reds='auto', get_printable_location=get_location)


def jitpolicy(driver):
    try:
        from rpython.jit.codewriter.policy import JitPolicy
        return JitPolicy()
    except ImportError:
        raise NotImplemented("Abandon if we are unable to use RPython's JitPolicy")
# end of RPython setup


def read_file(filename):
    fd = os.open(filename, os.O_RDONLY, 0o777)
    text = ""

    while True:
        read = os.read(fd, 4096)
        if len(read) == 0:
            break
        text += read

    os.close(fd)
    return text


def main(argv):
    """Parse and run any E2 program"""
    
    # check for arguments
    try:
        file = argv[1]
    except IndexError:
        print("Expected one file name argument to be passed, e.g. ./parser program.tig")
        return 40

    program_contents = read_file(argv[1])
    
    # parse input program
    try:
        program = Parser(program_contents).parse()
    except ParseError as e:
        print("Parse failure: %s" % e.to_string())
        return 42

    # set debug level
    debug_level = 0
    try:
        debug_level = int(os.environ['DEBUG'])
    except KeyError:
        # there may be a better way to do this but RPython apparently does not allow "'DEBUG' in os.environ"
        pass

    # print the program
    jitdriver.jit_merge_point(code=program)
    print(program.to_string())

    return 0


if __name__ == "__main__":
    code = main(sys.argv)
    sys.exit(code)


def target(*args):
    return main, None
