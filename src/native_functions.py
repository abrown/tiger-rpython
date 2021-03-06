import os

from src.ast import IntegerValue, FunctionParameter, TypeId, StringValue, \
    NativeNoArgumentFunctionDeclaration, NativeOneArgumentFunctionDeclaration, NativeFunctionDeclaration, Let, \
    TypeDeclaration
from src.environment import Environment

try:
    from rpython.rlib.rtimer import read_timestamp
except ImportError:

    def read_timestamp():
        import time
        return int(time.clock() * 1000000)  # micro-seconds


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


STDOUT_FD = 1
STDERR_FD = 2


def tiger_print(value):
    """Native function to print Tiger values; will not append a newline"""
    if isinstance(value, IntegerValue):
        os.write(STDOUT_FD, str(value.integer))
    elif isinstance(value, StringValue):
        os.write(STDOUT_FD, value.string)
    else:
        raise ValueError('Unknown value type %s' % value.__class__.__name__)


class Timestamp:
    """
    Number of ticks (RPython); wall clock time (Python)
    """
    value = 0


start_timestamp = Timestamp()


def tiger_start_timer():
    """Native function to start a timer; in RPython this will measure the CPU ticks with RDTSC, see
    genop_math_read_timestamp in pypy/rpython/jit/backend/x86/assembler.py"""
    start_timestamp.value = read_timestamp()
    return IntegerValue(start_timestamp.value)


def tiger_stop_timer():
    """Native function to stop the timer timer, printing out the number of ticks; see tiger_start_timer()"""
    end_timestamp = read_timestamp()
    total_time = end_timestamp - start_timestamp.value
    try:
        if int(os.environ['DEBUG']):
            os.write(STDERR_FD, "ticks=%d\n" % total_time)
    except KeyError:
        # sure would like to avoid this try-catch
        pass
    return IntegerValue(total_time)


def create_native_functions():
    """Convenience method to add all native functions to the environment"""
    string_type = TypeId('string')
    integer_type = TypeId('int')
    native_types = Let([TypeDeclaration('string', string_type), TypeDeclaration('int', integer_type)], [])
    print_function = NativeOneArgumentFunctionDeclaration('print', [FunctionParameter('message', string_type)],
                                                          None, tiger_print)
    time_go_function = NativeNoArgumentFunctionDeclaration('timeGo', integer_type, tiger_start_timer)
    time_stop_function = NativeNoArgumentFunctionDeclaration('timeStop', integer_type, tiger_stop_timer)
    return [native_types, print_function, time_go_function, time_stop_function]


def create_environment_with_natives():
    """Convenience method to add all native functions to the environment"""
    environment = Environment.empty().push(4)
    native_functions = create_native_functions()
    for i in range(len(native_functions)):
        environment.set(i, native_functions[i])
    return environment  # TODO remove this


def create_empty_environment():
    return Environment.empty()



def list_native_environment_names(env):
    """List the names of native functions in the environment; this expects all names to be in the current level"""
    assert isinstance(env, Environment)
    names = []
    for exp in env.expressions:
        if isinstance(exp, NativeFunctionDeclaration):
            names.append(exp.name)
    return names
