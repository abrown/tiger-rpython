import unittest

from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rtyper.llinterp import LLInterpreter
from rpython.translator.interactive import Translation

from src.ast import IntegerValue
from src.main.util import create_environment_with_natives
from src.parser import Parser

# Begin RPython setup; catch import errors so this can still run in CPython...
try:
    from rpython.rlib.jit import JitDriver, promote, hint
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


class TestExperiments(unittest.TestCase):
    def interpret_in_python(self, function, arguments):
        assert callable(function)
        assert isinstance(arguments, list)
        return function(*arguments)

    def interpret_as_jitcode(self, function, arguments):
        """Convert to JIT code and interpret the JIT code"""
        assert callable(function)
        assert isinstance(arguments, list)
        jit = LLJitMixin()
        return jit.interp_operations(function, arguments)

    def meta_interpret(self, function, arguments):
        """Interpret the function three different ways"""
        assert callable(function)
        assert isinstance(arguments, list)
        assert not any([not isinstance(a, int) for a in arguments]), "Remember not to pass in objects to meta_interpret"
        jit = LLJitMixin()
        return jit.meta_interp(function, arguments, listops=True, inline=True)

    def interpret_from_graph(self, rtyper, graph):
        """
        :param rtyper: see translation.driver.translator.rtyper
        :param graph: see translation.driver.translator.graphs[0]
        :return: the result
        """
        interpreter = LLInterpreter(rtyper)
        return interpreter.eval_graph(graph)  # interpret all translated operations

    def translate_to_graph(self, function, arguments):
        assert callable(function)
        assert isinstance(arguments, list)
        translation = Translation(function, arguments)
        translation.annotate()
        translation.rtype()
        translation.backendopt()
        translation.view()
        return translation.driver.translator.rtyper, translation.driver.translator.graphs[0]

    def test_simple_interpretation(self):
        def test(a, b):
            a = promote(a)
            b = promote(b)
            return compare(a, b)

        def compare(a, b):
            if a > b:
                return 42
            else:
                return 0

        self.assertEqual(self.interpret_in_python(test, [1, 0]), 42)
        self.assertEqual(self.interpret_as_jitcode(test, [1, 0]), 42)

    def test_simple_meta_interpretation_with_merge_point(self):
        driver = JitDriver(greens=[], reds='auto')

        def test(a, b):
            a = promote(a)
            b = promote(b)
            driver.jit_merge_point()
            return compare(a, b)

        def compare(a, b):
            if a > b:
                return 42
            else:
                return 0

        self.assertEqual(self.meta_interpret(test, [1, 0]), 42)

    def test_simple_translation_with_graph(self):
        def test(a, b):
            a = promote(a)
            b = promote(b)
            return a > b

        self.translate_to_graph(test, [int, int])

    def test_for_loop(self):
        def test():
            program = Parser("let var a := 0 in (for i := 1 to 9 do a := a + i; a) end").parse()
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(test(), 45)

        # 280+ operations
        # self.assertEqual(self.interpret_as_jitcode(test, []), 45)

        # 18 operations: the stderr trace of this looks almost exactly like the binary-run version (but has additional guard_nonnull_class checks, GcStruct fields
        self.assertEqual(self.meta_interpret(test, []), 45)


if __name__ == '__main__':
    unittest.main()
