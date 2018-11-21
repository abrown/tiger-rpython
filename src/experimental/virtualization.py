import unittest

import interpretation_mechanisms
# Begin RPython setup; catch import errors so this can still run in CPython...
from src.ast import Let, Add
from src.environments.environment_without_display import Environment

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


class Exp:
    _immutable_ = True

    def eval(self, env):
        raise NotImplementedError


class Box(Exp):
    _immutable_ = True

    def __init__(self, value):
        self.value = value

    @unroll_safe
    def eval(self, env):
        return self


class Ref(Exp):
    _immutable_ = True

    def __init__(self, x, y):
        self.x = x
        self.y = y

    @unroll_safe
    def eval(self, env):
        y = self.y
        while y:
            env = env.parent
            y -= 1
        return env.expressions[self.x]


class Add(Exp):
    _immutable_ = True

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def eval(self, env):
        lv = self.left.eval(env)
        rv = self.right.eval(env)
        return Box(lv.value + rv.value)


class Let(Exp):
    _immutable_ = True

    def __init__(self, box, exp):
        self.box = box
        self.exp = exp

    @unroll_safe
    def eval(self, env):
        env = env.push(1)
        env.expressions[0] = self.box
        result = self.exp.eval(env)
        env = env.pop()
        return result


class TestVirtualization(unittest.TestCase):
    """
    These tests attempt to virtualize the environment variables
    """

    def test_virtualized_while_loop_with_simple_environment(self):
        """
        Attempt to setup a scenario in which virtualization fails; however, it does not. The AST below attempts to
        resolve a reference 0-2 levels deep in a hierarchical environment. What I found:
         - @unroll_safe was necesary to avoid calls--added it to all nodes though perhaps it should not be on Loop
         - virtualizing Env.expressions[*] may have worked as expected (hard to tell); the boxed value was picked up from a previous pointer in the trace
         - the boxing seemed excessive so I added _immutable_ = True to every node; the trace length was cut in half
         - I removed the virtualization as it seemed to have no effect
         - adding an index to the Ref (so that it was not only parent-distance but also index-distance) seemed to have no effect
        """

        class Env:
            _immutable_ = True
            _virtualizable_ = 'expressions[*]'

            def __init__(self, parent, expressions):
                self.parent = parent or None
                self.expressions = expressions or []

            def push(self, size):
                return Env(self, [None] * size)

            def pop(self):
                return self.parent

        def get_location(exp):
            return exp.__class__.__name__

        jitdriver = JitDriver(greens=['exp'], reds=['t', 'r', 'env'], virtualizables=['env'],
                              get_printable_location=get_location)

        # jitdriver = JitDriver(greens=['exp'], reds=['t', 'r', 'env'], get_printable_location=get_location)

        class Loop(Exp):
            _immutable_ = True

            def __init__(self, times, exp):
                self.times = times
                self.exp = exp

            @unroll_safe
            def eval(self, env):
                result = None
                t = self.times
                while t:
                    jitdriver.jit_merge_point(exp=self, t=t, r=result, env=env)
                    result = self.exp.eval(env)
                    t -= 1
                return result

        def test(x, y):
            ast = Let(Box(42),
                      Let(Box(43),
                          Loop(10,
                               Let(Box(44),
                                   Add(Ref(x, y), Box(10))
                                   )
                               )
                          )
                      )
            env = Env(None, [])
            result = ast.eval(env)
            return result.value

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [0, 0]), 54)

    """
    Using Ref(2) it seems to do the lookup:
    
    [6d] {jit-log-opt-loop
    # Loop 1 (Loop) : loop with 33 ops
    [i0, p1, p2]
    label(i0, p1, p2, descr=TargetToken(139792829524560))
    debug_merge_point(0, 0, 'Loop')
    p4 = getfield_gc_r(ConstPtr(ptr3), descr=FieldDescr(<GcStruct optimizing_while_loops.Loop { super, inst_exp, inst_times }>, 'inst_exp'))
    guard_class(p4, <AddressAsInt * struct optimizing_while_loops.Let_vtable { super=... }>, descr=<Guard0x7f240dec81e0>) [p2, i0, p4]
    guard_class(p2, <AddressAsInt * struct optimizing_while_loops.Env_vtable { super=..., cls_pop=None, cls_push=None }>, descr=<Guard0x7f240df290f0>) [p2, i0, p4]
    p7 = getfield_gc_r(p4, descr=FieldDescr(<GcStruct optimizing_while_loops.Let { super, inst_box, inst_exp }>, 'inst_box'))
    p8 = getfield_gc_r(p4, descr=FieldDescr(<GcStruct optimizing_while_loops.Let { super, inst_box, inst_exp }>, 'inst_exp'))
    guard_class(p8, <AddressAsInt * struct optimizing_while_loops.Ref_vtable { super=... }>, descr=<Guard0x7f240df229b0>) [p2, i0, p4]
    i10 = getfield_gc_i(p8, descr=FieldDescr(<GcStruct optimizing_while_loops.Ref { super, inst_distance }>, 'inst_distance'))
    i11 = int_is_true(i10)
    guard_true(i11, descr=<Guard0x7f240df29280>) [p2, i0, p4]
    i13 = int_sub(i10, 1)
    i14 = int_is_true(i13)
    guard_true(i14, descr=<Guard0x7f240df224b0>) [p2, i0, p4]
    p15 = getfield_gc_r(p2, descr=FieldDescr(<GcStruct optimizing_while_loops.Env { super, vable_token, inst_boxes, inst_parent }>, 'inst_parent'))
    i17 = int_sub(i13, 1)
    i18 = int_is_true(i17)
    guard_false(i18, descr=<Guard0x7f240df22e60>) [p2, i0, p4]
    p19 = getfield_gc_r(p15, descr=FieldDescr(<GcStruct optimizing_while_loops.Env { super, vable_token, inst_boxes, inst_parent }>, 'inst_boxes'))
    p21 = getarrayitem_gc_r(p19, 0, descr=ArrayDescr(<GcArray of * GcStruct object { typeptr } >))
    i23 = int_sub(i0, 1)
    i24 = int_is_true(i23)
    guard_true(i24, descr=<Guard0x7f240df22be0>) [p2, i0, p4]
    debug_merge_point(0, 0, 'Loop')
    p25 = same_as_r(p21)
    label(i23, p21, p2, p4, p8, p15, p19, p25, descr=TargetToken(139792829522960))
    debug_merge_point(0, 0, 'Loop')
    i27 = int_sub(i23, 1)
    i28 = int_is_true(i27)
    guard_true(i28, descr=<Guard0x7f240df22280>) [p2, i27, p25]
    debug_merge_point(0, 0, 'Loop')
    i29 = arraylen_gc(p19, descr=ArrayDescr(<GcArray of * GcStruct object { typeptr } >))
    jump(i27, p25, p2, p4, p8, p15, p19, p25, descr=TargetToken(139792829522960))
    [6e] jit-log-opt-loop}
        bh: goto_if_not_int_is_true [0, 45, 42] -> 45
        bh: ref_return [<BHInterp #1>, <* GCREF hidden>] -> LeaveFrame!
    DoneWithThisFrameRef
    [6e] jit-tracing}
    ~~~ return value: 42
    """

    """
    Using Ref(0) it seems to virtualize the value:
    
    # Loop 1 (Loop) : loop with 23 ops
    [i0, p1, p2]
    label(i0, p1, p2, descr=TargetToken(140519484847120))
    debug_merge_point(0, 0, 'Loop')
    p4 = getfield_gc_r(ConstPtr(ptr3), descr=FieldDescr(<GcStruct optimizing_while_loops.Loop { super, inst_exp, inst_times }>, 'inst_exp'))
    guard_class(p4, <AddressAsInt * struct optimizing_while_loops.Let_vtable { super=... }>, descr=<Guard0x7fcd3df8f6e0>) [p2, i0, p4]
    guard_class(p2, <AddressAsInt * struct optimizing_while_loops.Env_vtable { super=..., cls_pop=None, cls_push=None }>, descr=<Guard0x7fcd3df8f5f0>) [p2, i0, p4]
    p7 = getfield_gc_r(p4, descr=FieldDescr(<GcStruct optimizing_while_loops.Let { super, inst_box, inst_exp }>, 'inst_box'))
    p8 = getfield_gc_r(p4, descr=FieldDescr(<GcStruct optimizing_while_loops.Let { super, inst_box, inst_exp }>, 'inst_exp'))
    guard_class(p8, <AddressAsInt * struct optimizing_while_loops.Ref_vtable { super=... }>, descr=<Guard0x7fcd3dfa7780>) [p2, i0, p4]
    i10 = getfield_gc_i(p8, descr=FieldDescr(<GcStruct optimizing_while_loops.Ref { super, inst_distance }>, 'inst_distance'))
    i11 = int_is_true(i10)
    guard_false(i11, descr=<Guard0x7fcd3df8f690>) [p2, i0, p4]
    i13 = int_sub(i0, 1)
    i14 = int_is_true(i13)
    guard_true(i14, descr=<Guard0x7fcd3dfa77d0>) [p2, i0, p4]
    debug_merge_point(0, 0, 'Loop')
    p15 = same_as_r(p7)
    label(i13, p7, p2, p4, p8, p15, descr=TargetToken(140519484847280))
    debug_merge_point(0, 0, 'Loop')
    i17 = int_sub(i13, 1)
    i18 = int_is_true(i17)
    guard_true(i18, descr=<Guard0x7fcd3dfa7550>) [p2, i17, p15]
    debug_merge_point(0, 0, 'Loop')
    jump(i17, p15, p2, p4, p8, p15, descr=TargetToken(140519484847280))
    [6f] jit-log-opt-loop}
        bh: goto_if_not_int_is_true [0, 45, 42] -> 45
        bh: ref_return [<BHInterp #1>, <* GCREF hidden>] -> LeaveFrame!
    DoneWithThisFrameRef
    [6f] jit-tracing}
    ~~~ return value: 44
    """

    """
    After immutable changes, Ref(0) is at 14 ops:
    [63] {jit-log-opt-loop
    # Loop 1 (Loop) : loop with 14 ops
    [i0, p1, p2]
    label(i0, p1, p2, descr=TargetToken(139814559890960))
    debug_merge_point(0, 0, 'Loop')
    guard_class(p2, <AddressAsInt * struct virtualization.Env_vtable { super=..., cls_pop=None, cls_push=None }>, descr=<Guard0x7f291d2d33c0>) [p2, i0]
    i5 = int_sub(i0, 1)
    i6 = int_is_true(i5)
    guard_true(i6, descr=<Guard0x7f291d2d32d0>) [p2, i0]
    debug_merge_point(0, 0, 'Loop')
    label(i5, p2, descr=TargetToken(139814559888240))
    debug_merge_point(0, 0, 'Loop')
    i8 = int_sub(i5, 1)
    i9 = int_is_true(i8)
    guard_true(i9, descr=<Guard0x7f291d3e91e0>) [p2, i8]
    debug_merge_point(0, 0, 'Loop')
    jump(i8, p2, descr=TargetToken(139814559888240))
    [63] jit-log-opt-loop}
        bh: goto_if_not_int_is_true [0, 45, 42] -> 45
        bh: ref_return [<BHInterp #1>, <* GCREF hidden>] -> LeaveFrame!
    DoneWithThisFrameRef
    """

    def test_virtualized_while_loop_with_current_environment(self):
        """
        Now attempt the scenario above but with the actual environment implementation used in the Tiger interpreter
        """

        Environment._virtualizable_ = ['expressions[*]']

        def get_location(exp):
            return exp.__class__.__name__

        jitdriver = JitDriver(greens=['exp'], reds=['t', 'r', 'env'], virtualizables=['env'],
                              get_printable_location=get_location)

        # jitdriver = JitDriver(greens=['exp'], reds=['t', 'r', 'env'], get_printable_location=get_location)

        class Loop(Exp):
            _immutable_ = True

            def __init__(self, times, exp):
                self.times = times
                self.exp = exp

            @unroll_safe
            def eval(self, env):
                result = None
                t = self.times
                while t:
                    jitdriver.jit_merge_point(exp=self, t=t, r=result, env=env)
                    result = self.exp.eval(env)
                    t -= 1
                return result

        def test(x, y):
            ast = Let(Box(42),
                      Let(Box(43),
                          Loop(10,
                               Let(Box(44),
                                   Add(Ref(x, y), Box(10))
                                   )
                               )
                          )
                      )
            env = Environment.empty()
            result = ast.eval(env)
            return result.value

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [0, 0]), 54)


if __name__ == '__main__':
    unittest.main()
