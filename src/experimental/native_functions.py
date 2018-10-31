import unittest

import interpretation_mechanisms

# Begin RPython setup; catch import errors so this can still run in CPython...

try:
    from rpython.rlib.jit import JitDriver, promote, hint, dont_look_inside, loop_invariant, elidable, unroll_safe
except ImportError:
    class JitDriver(object):
        def __init__(self, **kw): pass

        def jit_merge_point(self, **kw):
            pass

        def can_enter_jit(self, **kw):
            pass


    def promote(x):
        return x


    def hint(x, **kwds):
        return x


    def dont_look_inside(func):
        return func


    def loop_invariant(func):
        return func


    def elidable(func):
        return func


    def unroll_safe(func):
        return func


class TestNativeFunctions(unittest.TestCase):
    """
    These tests show the difficulty of trying to use RPython to dynamically select native functions within an
    interpreter"""

    def test_not_working_example(self):
        """
        We build a list of AST nodes: some are one-arg native functions and some are zero-arg native functions. RPython
        seems unable to determine which one it is virtually dispatching to:

        AnnotatorError:

        signature mismatch: native_print_newline() takes no arguments (1 given)


        Occurred processing the following simple_call:
          function native_print_newline <.../src/experimental/native_functions.py, line 76> returning

          function native_print <.../src/experimental/native_functions.py, line 72> returning

            v2 = simple_call(v0, v1)

        In <FunctionGraph of (native_functions:69)OneArgFunction.call at 0x7f714ff320d0>:
        Happened at file .../src/experimental/native_functions.py line 70

        ==>                 return self.function(arguments[0])

        Known variable annotations:
         v0 = SomePBC(can_be_None=False, descriptions={...2...}, knowntype=function, subset_of=None)
         v1 = SomeString(no_nul=True)
        """

        class NativeFunction:
            def __init__(self, function):
                self.function = function

            def call(self, arguments):
                raise Exception("Use descendants")

        class ZeroArgFunction(NativeFunction):
            def call(self, arguments):
                return self.function()

        def native_print_newline():
            print('no-arg\n')
            return 1

        class OneArgFunction(NativeFunction):
            def call(self, arguments):
                return self.function(arguments[0])

        def native_print(s):
            print('one-arg: %s\n' % s)
            return len(s)

        def get_location(code):
            return "%s" % code.__class__.__name__

        jitdriver = JitDriver(greens=['code'], reds='auto', get_printable_location=get_location)

        def test(a, b, c):
            arguments = ['as', 'b', 'c']
            assert isinstance(arguments, list)
            program = [ZeroArgFunction(native_print_newline), OneArgFunction(native_print),
                       ZeroArgFunction(native_print_newline)]
            result = 0
            for node in program:
                jitdriver.jit_merge_point(code=node)
                result = node.call(arguments)
            return result

        # eventually calls something like: return LLJitMixin().meta_interp(function, arguments, listops=True, inline=True)
        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [41, 42, 43]), 1)

    def test_working_example(self):
        """
        With help from the PyPy crew (Alex Gaynor, Antonio Cuni, see
        https://botbot.me/freenode/pypy/2018-10-31/?msg=105890623&page=1) I was able to get the above to work
        """

        class NativeFunction:
            _attrs_ = []

            def call(self, arguments):
                raise Exception("Use descendants")

        class ZeroArgFunction(NativeFunction):
            _attrs_ = ['function']

            def __init__(self, function):
                self.function = function

            def call(self, arguments):
                return self.function()

        def native_print_newline():
            print('no-arg\n')
            return 1

        class OneArgFunction(NativeFunction):
            _attrs_ = ['function']

            def __init__(self, function):
                self.function = function

            def call(self, arguments):
                return self.function(arguments[0])

        def native_print(s):
            print('one-arg: %s\n' % s)
            return len(s)

        def get_location(code):
            return "%s" % code.__class__.__name__

        jitdriver = JitDriver(greens=['code'], reds='auto', get_printable_location=get_location)

        def test(a, b, c):
            arguments = ['as', 'b', 'c']
            assert isinstance(arguments, list)
            program = [ZeroArgFunction(native_print_newline), OneArgFunction(native_print),
                       ZeroArgFunction(native_print_newline)]
            result = 0
            for node in program:
                jitdriver.jit_merge_point(code=node)
                result = node.call(arguments)
            return result

        # eventually calls something like: return LLJitMixin().meta_interp(function, arguments, listops=True, inline=True)
        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [41, 42, 43]), 1)


if __name__ == '__main__':
    unittest.main()
