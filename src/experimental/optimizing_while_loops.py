import unittest

import interpretation_mechanisms
# Begin RPython setup; catch import errors so this can still run in CPython...
from src.ast import IntegerValue, BreakException, Let, VariableDeclaration, Sequence, LValue, Assign, While, LessThan, \
    Add
from src.environments.environment_without_display import Environment
from src.native_functions import create_environment_with_natives
from src.parser import Parser

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


class TestOptimizingWhileLoops(unittest.TestCase):
    """
    These tests show the effects of different attempts to optimize Tiger while loops. The tests all operate on the same
    basic algorithm:
     - set a to 0
     - repeatedly increment a by 1 until it is 100 or greater
    """

    def test_current_implementation(self):
        """
        # Loop 1 (While(condition=LessThan(left=LValue(name=a, next=None), right=IntegerValue(100)), body=Assign(lvalue=
        LValue(name=a, next=None), expression=Add(left=LValue(name=a, next=None), right=IntegerValue(1))))) :
        loop with 88 ops
        """

        def test():
            program = Parser('let var a := 0 in (while a < 100 do a := a + 1; a) end').parse()
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 100)

    def test_larger_merge_point_key(self):
        """
        This has the same merge point location as the current implementation but uses a merge point key with more
        variables: code, expression, environment. I found that this larger merge point key not only failed to recognize
        loops in sumprimes but the JIT-compiling binary would not terminate.

        # Loop 1 (ModifiedWhile(condition=LessThan(left=LValue(name=a, next=None), right=IntegerValue(100)), body=Assign
        (lvalue=LValue(name=a, next=None), expression=Add(left=LValue(name=a, next=None), right=IntegerValue(1))))) :
        loop with 85 ops
        """

        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        class ModifiedWhile(While):
            _immutable_ = True

            def evaluate(self, env):
                condition_value = self.condition.evaluate(env)
                assert isinstance(condition_value, IntegerValue)

                result = None
                while condition_value.integer != 0:
                    jitdriver.jit_merge_point(code=self, expression=self.body, environment=env)
                    try:
                        result = self.body.evaluate(env)
                    except BreakException:
                        break
                    condition_value = self.condition.evaluate(env)

                return result

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            Parser('let var a := 0 in a end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[ModifiedWhile(condition=LessThan(left=LValue('a'), right=IntegerValue(100)),
                                                         body=Assign(lvalue=LValue(name='a'),
                                                                     expression=Add(
                                                                         left=LValue(name='a'),
                                                                         right=IntegerValue(1)))),
                                           LValue(name='a', next=None)])])
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 100)

    def test_nested_while_loops(self):
        """
        Weirdly, this test takes about 80 seconds on my machine. It has one bridge and two loops:

        # Loop 1 (ModifiedWhile(condition=LessThan(left=LValue(name=b, next=None), right=IntegerValue(100)), body=Sequen
        ce(expressions=[Assign(lvalue=LValue(name=b, next=None), expression=Add(left=LValue(name=b, next=None), right=In
        tegerValue(1)))]))) : loop with 123 ops

        # Loop 3 (ModifiedWhile(condition=LessThan(left=LValue(name=a, next=None), right=IntegerValue(50)), body=Sequenc
        e(expressions=[Assign(lvalue=LValue(name=a, next=None), expression=Add(left=LValue(name=a, next=None), right=Int
        egerValue(1))), ModifiedWhile(condition=LessThan(left=LValue(name=b, next=None), right=IntegerValue(100)), body=
        Sequence(expressions=[Assign(lvalue=LValue(name=b, next=None), expression=Add(left=LValue(name=b, next=None), ri
        ght=IntegerValue(1)))])), Assign(lvalue=LValue(name=b, next=None), expression=IntegerValue(0))]))) :
        loop with 231 ops
        """

        def get_location(code):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code'], reds='auto',
                              get_printable_location=get_location)

        class ModifiedWhile(While):
            _immutable_ = True

            def evaluate(self, env):
                condition_value = self.condition.evaluate(env)
                assert isinstance(condition_value, IntegerValue)

                result = None
                while condition_value.integer != 0:
                    jitdriver.jit_merge_point(code=self)
                    try:
                        result = self.body.evaluate(env)
                    except BreakException:
                        break
                    condition_value = self.condition.evaluate(env)

                return result

        def test():
            # this is equivalent to what is constructed below
            unused = Parser("""
            let var a := 0 var b := 0 in 
                (while a < 50 do
                   (a := a + 1;
                   while b < 100 do
                       (b := b + 1);
                    b := 0
                   );
                a)
            end""").parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0)),
                                        VariableDeclaration(name='b', type=None, exp=IntegerValue(0))],
                          expressions=[
                              Sequence(expressions=[
                                  ModifiedWhile(
                                      condition=LessThan(left=LValue(name='a', next=None), right=IntegerValue(50)),
                                      body=Sequence(expressions=[
                                          Assign(lvalue=LValue(name='a', next=None),
                                                 expression=Add(left=LValue(name='a', next=None),
                                                                right=IntegerValue(1))),
                                          ModifiedWhile(condition=LessThan(left=LValue(name='b', next=None),
                                                                           right=IntegerValue(100)),
                                                        body=Sequence(expressions=[
                                                            Assign(lvalue=LValue(name='b', next=None), expression=Add(
                                                                left=LValue(name='b', next=None),
                                                                right=IntegerValue(1)))])),
                                          Assign(lvalue=LValue(name='b', next=None), expression=IntegerValue(0))])),
                                  LValue(name='a', next=None)])])

            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 50)
        # self.assertEqual(self.interpret_as_jitcode(test, []), 100)
        # self.assertEqual(self.interpret_in_python(test, []), 50)
        # self.assertEqual(self.interpret_from_graph(test, []), 100)

    def test_sumprimes(self):
        def test():
            program = Parser("""
            let
              var max : int := 50
              var s : int := 0
              var n : int := 2
            in
              while n <= max do
                 let
                    var p : int := 1
                    var d : int := 2
                  in
                    while d <= (n - 1) do
                       let
                         var m : int := d * (n / d)
                       in
                         if n <= m then
                           p := 0;
                         d := d + 1
                       end;
                     if p <> 0 then
                       s := s + n;
                     n := n + 1
                  end;
               s
            end
            """).parse()

            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 328)

    def test_virtualized_while_loop_changed_merge_point_with_virtualizable(self):
        """
        This is a (currently failed) attempt to virtualize the current level's local variables through the environment
        display
        """

        # requires enabling _virtualizable_ in Environment
        Environment._virtualizable_ = ['expressions[*]']

        # def init(s, *args):
        #     s = hint(s, access_directly=True, fresh_virtualizable=True)
        #     Environment.__init__(*args)
        #
        # Environment.__init__ = init

        hint(self, access_directly=True, fresh_virtualizable=True)

        def get_location(code):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code'], reds=['env', 'result'], virtualizables=['env'], get_printable_location=get_location)
        #jitdriver = JitDriver(greens=['code'], reds=['env', 'result'], get_printable_location=get_location)

        class ModifiedWhile(While):
            _immutable_ = True

            def evaluate(self, env):
                condition_value = self.condition.evaluate(env)
                assert isinstance(condition_value, IntegerValue)

                # env = hint(env, access_directly=True)
                # env = hint(env, access_directly=True, fresh_virtualizable=True)
                # vars = env.expressions
                # vars = hint(vars, access_directly=True)
                # env = hint(env, access_directly=True)
                result = None
                while condition_value.integer != 0:
                    jitdriver.jit_merge_point(code=self, env=env, result=result)
                    try:
                        result = self.body.evaluate(env)
                    except BreakException:
                        break
                    condition_value = self.condition.evaluate(env)

                return result

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            unused = Parser('let var a := 0 in (while a < 100 do a := a + 1) end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[ModifiedWhile(condition=LessThan(left=LValue('a'), right=IntegerValue(100)),
                                                         body=Assign(lvalue=LValue(name='a'),
                                                                     expression=Add(
                                                                         left=LValue(name='a'),
                                                                         right=IntegerValue(1)))),
                                           LValue(name='a', next=None)])])

            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), 100)

    def test_sample_virtualized_while_loop(self):
        """
        Attempt to setup a scenario in which virtualization fails; however, it does not. The AST below attempts to
        resolve a reference 0-2 levels deep in a hierarchical environment. What I found:
         - @unroll_safe was necesary to avoid calls--added it to all nodes though perhaps it should not be on Loop
         - virtualizing Env.boxes[*] may have worked as expected (hard to tell); the boxed value was picked up from a previous pointer in the trace
         - the boxing seemed excessive so I added _immutable_ = True to every node; the trace length was cut in half
         - I removed the virtualization as it seemed to have no effect
         - adding an index to the Ref (so that it was not only parent-distance but also index-distance) seemed to have no effect
        """
        class Env:
            _immutable_ = True
            _virtualizable_ = 'boxes[*]'

            def __init__(self, parent, boxes):
                self.parent = parent or None
                self.boxes = boxes or []

            def push(self, size):
                return Env(self, [None] * size)

            def pop(self):
                return self.parent

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
                return env.boxes[self.x]

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
                env.boxes[0] = self.box
                result = self.exp.eval(env)
                env = env.pop()
                return result

        def get_location(exp):
            return exp.__class__.__name__

        jitdriver = JitDriver(greens=['exp'], reds=['t', 'r', 'env'], virtualizables=['env'], get_printable_location=get_location)
        #jitdriver = JitDriver(greens=['exp'], reds=['t', 'r', 'env'], get_printable_location=get_location)

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

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, [0, 2]), 54)

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


if __name__ == '__main__':
    unittest.main()
