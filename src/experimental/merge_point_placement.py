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


class TestMergePointPlacement(unittest.TestCase):
    """
    These tests try to show the effect of moving the jit_merge_point and can_enter_jit annotations; the algorithm should:
     - A: repeatedly increment y by 2 until it reaches 100
     - B: increment x by 1 and reset y to 0
     - C: repeatedly increment x until it reaches a number divisible by 10, then start again from A
     - stop and return xs only when x grows above 100
    """

    def test_merge_point_inside_branch_a(self):
        """
        Placing the merge point inside branch A (from above) results in the four of the additions to y being compiled
        in to a 13-operation trace and the additions to x in B and C being executed in the blackhole interpreter
        """

        def get_location(x):
            return "x=%d" % x

        jitdriver = JitDriver(greens=['x'], reds=['y'], get_printable_location=get_location)

        def test():
            x = 1
            y = 0
            while True:
                if x % 10 == 0:
                    y += 2
                    jitdriver.jit_merge_point(x=x, y=y)
                    # it does not make sense to: y = promote(y)
                    # this causes the traces to promptly fail when the guard on y is invalidated
                    if y >= 100:
                        y = 0
                        x += 1
                elif x >= 100:
                    break
                else:
                    x += 1
            return x

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 101)

        """
        Observe how the merge point is the first real instruction; no loop_header here because can_enter_jit is not used:
        
        [jitcodewriter:info] making JitCodes...
        test:
           0  L1:
           0  -live- %i0, %i1
           0  int_guard_value %i0
           2  -live- %i0, %i1
           2  jit_merge_point $0, I[%i0], R[], F[], I[%i1], R[], F[]
          12  -live- %i0, %i1
          12  -live- %i0, %i1
          12  goto_if_not_int_ge %i1, $100, L2
          17  int_add %i0, $1 -> %i0
          21  int_copy $0 -> %i1
          24  L3:
          24  residual_call_ir_i $<* fn ll_int_py_mod_nonnegargs__Signed_Signed>, I[%i0, $10], R[], CallDescr(<Signed>, (<Signed>, <Signed>), <EffectInfo 0x7fb8d1fb3ed0: EF=0 OS=14>) -> %i2
          33  -live- %i0, %i1, %i2
          33  goto_if_not_int_is_zero %i2, L4
          37  int_add %i1, $2 -> %i1
          41  goto L1
          44  ---
          44  L4:
          44  -live- %i0, %i1
          44  goto_if_not_int_ge %i0, $100, L5
          49  int_return %i0
          51  ---
          51  L5:
          51  int_add %i0, $1 -> %i0
          55  goto L3
          58  ---
          58  L2:
          58  goto L3
        """

    def test_merge_point_with_both_x_and_y(self):
        """
        Keying the merge point on both x and y does not make sense: no traces are ever produced because the hash of
        x and y is never the same value twice.
        """

        def get_location(x, y):
            return "x=%d, y=%d" % (x, y)

        jitdriver = JitDriver(greens=['x', 'y'], reds='auto', get_printable_location=get_location)

        def test():
            x = 1
            y = 0
            while True:
                if x % 10 == 0:
                    y += 2
                    jitdriver.jit_merge_point(x=x, y=y)
                    if y >= 100:
                        y = 0
                        x += 1
                elif x >= 100:
                    break
                else:
                    x += 1
            return x

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 101)

    def test_merge_point_with_can_enter_jit(self):
        """
        When a can_enter_jit is placed in A and the merge point is moved to the top of the "dispatch loop", we see the
        same 13-operation trace as in 'test_merge_point_inside_branch_a' but instead of B and C both being executed
        in the blackhole interpreter, we only see B. The additions for C (e.g. incrementing x from 81 to 90) are
        executed in the normal (non-trace, non-blackhole) interpreter.
        """

        def get_location(x):
            return "x=%d" % (x)

        jitdriver = JitDriver(greens=['x'], reds=['y'], get_printable_location=get_location)

        def test():
            x = 1
            y = 0
            while True:
                jitdriver.jit_merge_point(x=x, y=y)
                if x % 10 == 0:
                    y += 2
                    jitdriver.can_enter_jit(x=x, y=y)
                    if y >= 100:
                        y = 0
                        x += 1
                elif x >= 100:
                    break
                else:
                    x += 1
            return x

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 101)

        """
        NOTE: observe how the merge point and loop_header are placed in this example--the merge point is always the first
        real instruction:
        [jitcodewriter:info] making JitCodes...
        test:
           0  L1:
           0  -live- %i0, %i1
           0  int_guard_value %i0
           2  -live- %i0, %i1
           2  jit_merge_point $0, I[%i0], R[], F[], I[%i1], R[], F[]
          12  -live- %i0, %i1
          12  residual_call_ir_i $<* fn ll_int_py_mod_nonnegargs__Signed_Signed>, I[%i0, $10], R[], CallDescr(<Signed>, (<Signed>, <Signed>), <EffectInfo 0x7f3c4cd0d510: EF=0 OS=14>) -> %i2
          21  -live- %i0, %i1, %i2
          21  goto_if_not_int_is_zero %i2, L2
          25  int_add %i1, $2 -> %i1
          29  loop_header $0
          31  -live- %i0, %i1
          31  goto_if_not_int_ge %i1, $100, L3
          36  int_add %i0, $1 -> %i0
          40  int_copy $0 -> %i1
          43  L4:
          43  goto L1
          46  ---
          46  L3:
          46  goto L4
          49  ---
          49  L2:
          49  -live- %i0, %i1
          49  goto_if_not_int_ge %i0, $100, L5
          54  int_return %i0
          56  ---
          56  L5:
          56  int_add %i0, $1 -> %i0
          60  goto L4
        
        [jitcodewriter:info] there are 1 JitCode instances.
        """


if __name__ == '__main__':
    unittest.main()
