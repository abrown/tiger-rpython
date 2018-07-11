import unittest

from rpython.translator.interactive import Translation
from rpython.rtyper.llinterp import LLInterpreter
from rpython.jit.metainterp.test.support import LLJitMixin

# from src.main.tiger_interpreter import main

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

    def test_meta_interpretation_with_merge_point(self):
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

    def test_translate(self):
        def test(a, b):
            a = promote(a)
            b = promote(b)
            return a > b

        self.translate_to_graph(test, [int, int])


if __name__ == '__main__':
    unittest.main()
