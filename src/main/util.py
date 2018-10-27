import os

from src.ast import IntegerValue, NativeFunctionDeclaration, FunctionParameter, TypeId, StringValue
from src.environment import Environment

try:
    from rpython.rlib.jit import JitDriver
except ImportError:
    class JitDriver(object):
        def __init__(self, **kw): pass

        def jit_merge_point(self, **kw): pass

jitdriver = JitDriver(greens=['code'], reds='auto')


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


def trick_rpython_into_jit_compiling():
    a = IntegerValue(42)
    b = a.to_string()
    jitdriver.jit_merge_point(code=b)
    return b


STDOUT_FD = 1
STDERR_FD = 2


def tiger_print(value):
    if isinstance(value, IntegerValue):
        os.write(STDOUT_FD, str(value.integer))
    elif isinstance(value, StringValue):
        os.write(STDOUT_FD, value.string)
    else:
        raise ValueError('Unknown value type %s' % value.__class__.__name__)


def create_environment_with_natives():
    environment = Environment.empty().push(1)
    environment.set((0, 0), NativeFunctionDeclaration('print', [FunctionParameter('string', TypeId('string'))], None,
                                                      tiger_print))
    return environment
