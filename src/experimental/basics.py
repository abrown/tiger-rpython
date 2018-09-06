import unittest

import interpretation_mechanisms

# Begin RPython setup; catch import errors so this can still run in CPython...
try:
    from rpython.rlib.jit import JitDriver, promote, hint, dont_look_inside, loop_invariant
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


class TestBasics(unittest.TestCase):
    """
    These tests demonstrate the basic functionality of some of the interpretation mechanisms; take a look at the
    test logs for the interesting output (e.g. traces)
    """

    def test_jitcode_interpretation(self):
        """
        Verify that jitcode interpretation works as expected
        """

        def test(a, b):
            a = promote(a)
            b = promote(b)
            return compare(a, b)

        def compare(a, b):
            if a > b:
                return 42
            else:
                return 0

        self.assertEqual(interpretation_mechanisms.interpret_in_python(test, [1, 0]), 42)
        self.assertEqual(interpretation_mechanisms.interpret_as_jitcode(test, [1, 0]), 42)
        # no meta-interpretation here because no merge point is annotated above
        # self.assertEqual(self.meta_interpret(test, [1, 0]), 42)

    def test_meta_interpretation(self):
        """
        Verify that meta-interpretation works as expected
        """

        def print_location(a):
            return "a=%d" % a

        jitdriver = JitDriver(greens=['a'], reds='auto', get_printable_location=print_location)

        def test(a, b):
            while a > b:
                jitdriver.jit_merge_point(a=a)
                b += 1
            return 42

        self.assertEqual(interpretation_mechanisms.interpret_in_python(test, [10, 0]), 42)
        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [10, 0]), 42)

    def test_graph_translation(self):
        """
        Verify that graph translation works as expected; a PyGame window show pop-up
        """
        def test(a, b):
            a = promote(a)
            b = promote(b)
            return a > b

        interpretation_mechanisms.translate_to_graph(test, [int, int])


if __name__ == '__main__':
    unittest.main()
