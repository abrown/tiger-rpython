import unittest

# Begin RPython setup; catch import errors so this can still run in CPython...
import interpretation_mechanisms

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


class TestExplainE2Aborts(unittest.TestCase):

    def test_current_implementation(self):
        """
        Create an E2-like scenario for tweaking the annotation locations; it seems to match one of the patterns in
        e2d-slow.py in that Sequence is repeated but here it is repeated forever TODO
        TODO still not sure exactly what code to write to get a switch in the jitcodes
        """

        class Exp:
            code = -1

        class Increment(Exp):
            code = 0

        class Decrement(Exp):
            code = 1

        class While(Exp):
            code = 2

            def __init__(self, less_than, body):
                self.less_than = less_than
                self.body = body

        class Sequence(Exp):
            code = 3

            def __init__(self, current, next=None):
                self.current = current
                self.next = next

        def get_location(code):
            return "%s" % code.__class__.__name__

        jitdriver = JitDriver(greens=['exp'], reds=['acc', 'code'], get_printable_location=get_location)

        def eval(exp, acc):
            code = exp.code
            jitdriver.jit_merge_point(exp=exp, acc=acc, code=code)
            code = promote(code)
            if code == 0:
                assert isinstance(exp, Increment)
                acc += 1
                return acc
            elif code == 1:
                assert isinstance(exp, Decrement)
                acc -= 1
                return acc
            elif code == 2:
                assert isinstance(exp, While)
                while acc < exp.less_than:
                    eval(exp.body, acc)
                    jitdriver.can_enter_jit(exp=exp, acc=acc, code=code)
                return 0
            elif code == 3:
                assert isinstance(exp, Sequence)
                end_value = eval(exp.current, acc)
                if exp.next:
                    return eval(exp.next, acc)
                else:
                    return end_value
            else:
                raise ValueError('Unknown expression type')

        def test(acc):
            program = While(10, Sequence(Increment(), Sequence(Decrement(), Increment())))
            return eval(program, acc)

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [0]), 100)
        # interpretation_mechanisms.translate_to_graph(test, [])
        # self.assertEqual(interpretation_mechanisms.interpret_in_python(test, []), 100)
        # self.assertEqual(interpretation_mechanisms.interpret_as_jitcode(test, [0]), 100)

        """
        NOTE: remember that RPython will try to optimize away constants, so leaving eval(program, 0) in test() will
        result in:
        
        Exception: The variable acc_0 of type <Signed> was not explicitly listed in _forcelink.  This issue can be 
        caused by a jitdriver.jit_merge_point() where some variable containing an int or str or instance is actually 
        known to be constant, e.g. always 42.
        
        One solution is to pass in the variable, as in test(acc) -> eval(program, acc)
        """


if __name__ == '__main__':
    unittest.main()
