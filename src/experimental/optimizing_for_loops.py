import unittest

import interpretation_mechanisms
# Begin RPython setup; catch import errors so this can still run in CPython...
from src.ast import IntegerValue, For, BreakException, Let, VariableDeclaration, Sequence, LValue, Assign, Subtract
from src.environment import Environment, EnvironmentLevel
from src.main.util import create_environment_with_natives
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


class TestOptimizingForLoops(unittest.TestCase):
    """
    These tests show the effects of different attempts to optimize Tiger for loops. The tests all operate on the same
    basic algorithm:
     - set a to 0
     - loop from 1 to 9, subtracting each number from a
     - return a (which should be -45)
    """

    def test_for_loop_converted_to_while(self):
        """
        This test shows the effect of converting a for-loop into a while-loop at construction time (the current
        implementation). When traced, the optimized trace has a merge point on:

        # Loop 1 (While(condition=LessThanOrEquals(left=LValue(name=i, next=None), right=IntegerValue(9)), body=Sequence
        (expressions=[Assign(lvalue=LValue(name=a, next=None), expression=Subtract(left=LValue(name=a, next=None), right
        =LValue(name=i, next=None))), Assign(lvalue=LValue(name=i, next=None), expression=Add(left=LValue(name=i, next=N
        one), right=IntegerValue(1)))]))) : loop with 231 ops

        Note (if jitcode printing is turned on, set 'verbose = True' in rpython/jit/metainterp/warmspot.py:277) how many
        jitcodes are produced: [jitcodewriter:info] there are 139 JitCode instances. Using Parser(...) to construct the
        AST ensures that the flow space contains more JIT-able code paths.
        """

        def test():
            program = Parser("let var a := 0 in (for i := 1 to 9 do a := a - i; a) end").parse()
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(test(), -45)

        # 280+ operations
        # self.assertEqual(self.interpret_as_jitcode(test, []), 45)

        # 18 operations: the stderr trace of this looks almost exactly like the binary-run version (but has additional guard_nonnull_class checks, GcStruct fields)
        # 15 operations: adding @unroll_safe to LValue.evaluate cuts some operations; Envinronment.get reduces down to getfield_gc_r of list.items, getarrayitem_gc_r from this array, getfield_gc_i from integerValue.integer
        # but this is incorrect because it jit-compiles an "entry bridge" not a loop
        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    def test_showing_fewer_jit_codes_with_no_parser(self):
        """
        This test is equivalent to the above test_for_loop_converted_to_while except that the Parser(...) is not used--
        the AST is constructed manually. Now, RPython sees fewer JIT-able code paths: [jitcodewriter:info] there are 76
        JitCode instances. This results in fewer operations (in this case):

        # Loop 1 (While(condition=LessThanOrEquals(left=LValue(name=i, next=None), right=IntegerValue(9)), body=Sequence
        (expressions=[Assign(lvalue=LValue(name=a, next=None), expression=Subtract(left=LValue(name=a, next=None), right
        =LValue(name=i, next=None))), Assign(lvalue=LValue(name=i, next=None), expression=Add(left=LValue(name=i, next=N
        one), right=IntegerValue(1)))]))) : loop with 162 ops
        """

        def test():
            # output of printing the parsed version: Let(declarations=[VariableDeclaration(name=a, type=None, exp=IntegerValue(0))], expressions=[Sequence(expressions=[For(var=i, start=IntegerValue(1), end=IntegerValue(9), body=Assign(lvalue=LValue(name=a, next=None), expression=Subtract(left=LValue(name=a, next=None), right=LValue(name=i, next=None)))), LValue(name=a, next=None)])])
            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[For(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                               body=Assign(lvalue=LValue(name='a', next=None),
                                                           expression=Subtract(
                                                               left=LValue(name='a', next=None),
                                                               right=LValue(name='i',
                                                                            next=None)))),
                                           LValue(name='a', next=None)])])
            program = promote(program)
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.interpret_in_python(test, []), -45)
        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    def test_showing_more_jit_codes_when_parsing_something_random(self):
        """
        This test is equivalent to the above test_showing_fewer_jit_codes_with_no_parser except that the Parser(...) IS
        used, but to parse something completely different. This brings the JIT code count back to what it was in
        test_for_loop_converted_to_while: [jitcodewriter:info] there are 76 JitCode instances. However, the manual
        construction keeps the loop size the same as test_showing_fewer_jit_codes_with_no_parser:

        # Loop 1 (While(condition=LessThanOrEquals(left=LValue(name=i, next=None), right=IntegerValue(9)), body=Sequence
        (expressions=[Assign(lvalue=LValue(name=a, next=None), expression=Subtract(left=LValue(name=a, next=None), right
        =LValue(name=i, next=None))), Assign(lvalue=LValue(name=i, next=None), expression=Add(left=LValue(name=i, next=N
        one), right=IntegerValue(1)))]))) : loop with 162 ops
        """

        def test():
            unused_program = Parser('let var a := 0 in a end')  # this is never used
            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[For(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                               body=Assign(lvalue=LValue(name='a', next=None),
                                                           expression=Subtract(
                                                               left=LValue(name='a', next=None),
                                                               right=LValue(name='i',
                                                                            next=None)))),
                                           LValue(name='a', next=None)])])
            program = promote(program)
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.interpret_in_python(test, []), -45)
        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    def test_merge_point_inside_a_called_function(self):
        """
        This test shows that the merge point must be carefully placed within the same basic block as the loop; the
        original for-loop implementation (i.e. no while conversion) is used and the merge point is located in a call
        to loop(). The trace is only 40 operations long (see end of method) but, though it does capture the 'a := a - i'
        subtraction of the loop body, it does not capture an expected backwards jump at the end of the trace. I believe
        that this is why it is classified not as a loop but as an entry bridge and results in no execution speed-up
        (see my results from spring 2018 term report).
        """

        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        # adding this in brings the number of operations down from 105 to 31... still not 18
        def loop(code, expression, environment):
            jitdriver.jit_merge_point(code=code, expression=expression, environment=environment)
            return expression.evaluate(environment)

        class ExternalMergePointFor(For):
            """
            This is the original implementation of a Tiger for-loop (i.e. no while conversion)
            """
            _immutable_ = True

            def evaluate(self, env):
                env.push()
                start_value = self.start.evaluate(env)
                assert isinstance(start_value, IntegerValue)
                end_value = self.end.evaluate(env)
                assert isinstance(end_value, IntegerValue)

                iterator = IntegerValue(start_value.integer)
                for i in range(iterator.integer, end_value.integer + 1):
                    iterator.integer = i
                    env.set_current_level(self.var, iterator)
                    try:
                        result = loop(self, self.body, env)
                        assert result is None
                    except BreakException:
                        break

                env.pop()

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            Parser('let var a := 0 in a end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[ExternalMergePointFor(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                                                 body=Assign(lvalue=LValue(name='a', next=None),
                                                                             expression=Subtract(
                                                                                 left=LValue(name='a', next=None),
                                                                                 right=LValue(name='i',
                                                                                              next=None)))),
                                           LValue(name='a', next=None)])])
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

        """
        [264] {jit-log-opt-loop
        # Loop 1 (ExternalMergePointFor(var=i, start=IntegerValue(1), end=IntegerValue(9), body=Assign(lvalue=LValue(name=a, next=None), expression=Subtract(left=LValue(name=a, next=None), right=LValue(name=i, next=None))))) : entry bridge with 40 ops
        []
        debug_merge_point(0, 0, 'ExternalMergePointFor(var=i. start=IntegerValue(1). end=IntegerValue(9). body=Assign(lvalue=LValue(name=a. next=None). expression=Subtract(left=LValue(name=a. next=None). right=LValue(name=i. next=None))))')
        p4 = call_r(ConstClass(Environment.__locate__), ConstPtr(ptr1), ConstPtr(ptr2), ConstPtr(ptr3), descr=CallDescr(<* GcStruct tuple2 { item0, item1 }>, (<* GcStruct src.environment.Environment { super, inst_local_types, inst_local_variables }>, <* GcStruct rpy_string { hash, chars }>, <* GcStruct src.environment.EnvironmentLevel { super, inst_bindings, inst_expressions, inst_parent }>), <EffectInfo 0x7fc436648350: EF=5>))
        guard_no_exception(descr=<Guard0x7fc436f27af0>) [p4]
        p5 = getfield_gc_r(p4, descr=FieldDescr(<GcStruct tuple2 { item0, item1 }>, 'item0'))
        i6 = getfield_gc_i(p4, descr=FieldDescr(<GcStruct tuple2 { item0, item1 }>, 'item1'))
        guard_nonnull(p5, descr=<Guard0x7fc436eb2640>) [p4]
        i8 = int_lt(i6, 0)
        guard_false(i8, descr=<Guard0x7fc436f11e60>) [p4]
        p9 = getfield_gc_r(p5, descr=FieldDescr(<GcStruct src.environment.EnvironmentLevel { super, inst_bindings, inst_expressions, inst_parent }>, 'inst_expressions'))
        p10 = getfield_gc_r(p9, descr=FieldDescr(<GcStruct list { length, items }>, 'items'))
        p11 = getarrayitem_gc_r(p10, i6, descr=ArrayDescr(<GcArray of * GcStruct object { typeptr } >))
        guard_nonnull_class(p11, ConstClass(IntegerValue), descr=<Guard0x7fc436ef1320>) [p4]
        p17 = call_r(ConstClass(Environment.__locate__), ConstPtr(ptr14), ConstPtr(ptr15), ConstPtr(ptr16), descr=CallDescr(<* GcStruct tuple2 { item0, item1 }>, (<* GcStruct src.environment.Environment { super, inst_local_types, inst_local_variables }>, <* GcStruct rpy_string { hash, chars }>, <* GcStruct src.environment.EnvironmentLevel { super, inst_bindings, inst_expressions, inst_parent }>), <EffectInfo 0x7fc436648350: EF=5>))
        guard_no_exception(descr=<Guard0x7fc436f112d0>) [p11, p17]
        p18 = getfield_gc_r(p17, descr=FieldDescr(<GcStruct tuple2 { item0, item1 }>, 'item0'))
        i19 = getfield_gc_i(p17, descr=FieldDescr(<GcStruct tuple2 { item0, item1 }>, 'item1'))
        guard_nonnull(p18, descr=<Guard0x7fc436f285f0>) [p11, p17]
        i21 = int_lt(i19, 0)
        guard_false(i21, descr=<Guard0x7fc436f28960>) [p11, p17]
        p22 = getfield_gc_r(p18, descr=FieldDescr(<GcStruct src.environment.EnvironmentLevel { super, inst_bindings, inst_expressions, inst_parent }>, 'inst_expressions'))
        p23 = getfield_gc_r(p22, descr=FieldDescr(<GcStruct list { length, items }>, 'items'))
        p24 = getarrayitem_gc_r(p23, i19, descr=ArrayDescr(<GcArray of * GcStruct object { typeptr } >))
        guard_nonnull_class(p24, ConstClass(IntegerValue), descr=<Guard0x7fc436f28a50>) [p11, p17]
        i26 = getfield_gc_i(p11, descr=FieldDescr(<GcStruct src.ast.Program { super, inst_arguments, inst_array, inst_body, inst_body_if_false, inst_body_if_true, inst_condition, inst_declarations, inst_end, inst_exp, inst_expression, inst_expressions, inst_field_positions, inst_field_types, inst_fields, inst_initial_value_expression, inst_integer, inst_left, inst_length, inst_length_expression, inst_lvalue, inst_name, inst_next, inst_parameters, inst_return_type, inst_right, inst_start, inst_string, inst_type, inst_type_id, inst_type_name, inst_values, inst_var }>, 'inst_integer'))
        i27 = getfield_gc_i(p24, descr=FieldDescr(<GcStruct src.ast.Program { super, inst_arguments, inst_array, inst_body, inst_body_if_false, inst_body_if_true, inst_condition, inst_declarations, inst_end, inst_exp, inst_expression, inst_expressions, inst_field_positions, inst_field_types, inst_fields, inst_initial_value_expression, inst_integer, inst_left, inst_length, inst_length_expression, inst_lvalue, inst_name, inst_next, inst_parameters, inst_return_type, inst_right, inst_start, inst_string, inst_type, inst_type_id, inst_type_name, inst_values, inst_var }>, 'inst_integer'))
        i28 = int_sub(i26, i27)
        p33 = call_r(ConstClass(Environment.__locate__), ConstPtr(ptr30), ConstPtr(ptr31), ConstPtr(ptr32), descr=CallDescr(<* GcStruct tuple2 { item0, item1 }>, (<* GcStruct src.environment.Environment { super, inst_local_types, inst_local_variables }>, <* GcStruct rpy_string { hash, chars }>, <* GcStruct src.environment.EnvironmentLevel { super, inst_bindings, inst_expressions, inst_parent }>), <EffectInfo 0x7fc436648350: EF=5>))
        guard_no_exception(descr=<Guard0x7fc436f28e10>) [p33, i28]
        p34 = getfield_gc_r(p33, descr=FieldDescr(<GcStruct tuple2 { item0, item1 }>, 'item0'))
        i35 = getfield_gc_i(p33, descr=FieldDescr(<GcStruct tuple2 { item0, item1 }>, 'item1'))
        guard_nonnull(p34, descr=<Guard0x7fc436f28780>) [p33, i28]
        p36 = getfield_gc_r(p34, descr=FieldDescr(<GcStruct src.environment.EnvironmentLevel { super, inst_bindings, inst_expressions, inst_parent }>, 'inst_expressions'))
        i38 = int_lt(i35, 0)
        guard_false(i38, descr=<Guard0x7fc436f23550>) [p33, i28]
        p39 = getfield_gc_r(p36, descr=FieldDescr(<GcStruct list { length, items }>, 'items'))
        p40 = new_with_vtable(descr=SizeDescr(<GcStruct src.ast.IntegerValue { super }>))
        setfield_gc(p40, i28, descr=FieldDescr(<GcStruct src.ast.Program { super, inst_arguments, inst_array, inst_body, inst_body_if_false, inst_body_if_true, inst_condition, inst_declarations, inst_end, inst_exp, inst_expression, inst_expressions, inst_field_positions, inst_field_types, inst_fields, inst_initial_value_expression, inst_integer, inst_left, inst_length, inst_length_expression, inst_lvalue, inst_name, inst_next, inst_parameters, inst_return_type, inst_right, inst_start, inst_string, inst_type, inst_type_id, inst_type_name, inst_values, inst_var }>, 'inst_integer'))
        setarrayitem_gc(p39, i35, p40, descr=ArrayDescr(<GcArray of * GcStruct object { typeptr } >))
        leave_portal_frame(1)
        finish(ConstPtr(null), descr=<rpython.jit.metainterp.compile.DoneWithThisFrameDescrRef object at 0x7fc4376bdc80>)
        [271] jit-log-opt-loop}
        """

    def test_merge_point_in_the_middle_of_a_block(self):
        """
        If, unlike test_merge_point_inside_a_called_function, we place the merge point inside the looped block (inside
        the RPython while) we see more operations, but the trace ends in a jump operation and is classified as a loop:

        Loop 1 (InternalMergePointFor(var=i, start=IntegerValue(1), end=IntegerValue(9), body=Assign(lvalue=LValue(name=
        a, next=None), expression=Subtract(left=LValue(name=a, next=None), right=LValue(name=i, next=None))))) :
        loop with 110 ops


        This test will output  lines of 'bh: ...' logging at the end (see
        https://morepypy.blogspot.com/2010/06/blackhole-interpreter.html for more info); this is due, I believe, to the
        stop exception thrown to exit the RPython for-loop:

        bh: goto_if_not_int_ge [10, 10, 17, 15] -> 15
        bh: raise [<BHInterp #2>, <* GCREF hidden>] -> LLException!
        bh: goto_if_exception_mismatch [<BHInterp #1>, <AddressAsInt * struct exceptions.StopIteration_vtable { super=... }>, 103, 93] -> 93
        bh: guard_class [<rpython.jit.backend.llgraph.runner.LLGraphCPU object at 0x7f4a8fe91390>, <* GCREF hidden>] -> <AddressAsInt * struct src.environment.Environment_vtable { super=..., cls___locate__=None, cls_add=None, cls_clone=None, cls_get=None, cls_pop=None, cls_push=None, cls_set=None, cls_set_current_level=None }>
        bh: inline_call_r_v [<rpython.jit.backend.llgraph.runner.LLGraphCPU object at 0x7f4a8fe91390>, <JitCode 'Environment.pop'>, [<* GCREF hidden>]]
        bh: ref_return [<BHInterp #1>, <* None>] -> LeaveFrame!
        """

        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        class InternalMergePointFor(For):
            """
            This is the original implementation of a Tiger for-loop (i.e. no while conversion)
            """
            _immutable_ = True

            def evaluate(self, env):
                env.push()
                start_value = self.start.evaluate(env)
                assert isinstance(start_value, IntegerValue)
                end_value = self.end.evaluate(env)
                assert isinstance(end_value, IntegerValue)

                iterator = IntegerValue(start_value.integer)
                for i in range(iterator.integer, end_value.integer + 1):
                    iterator.integer = i
                    env.set_current_level(self.var, iterator)
                    try:
                        jitdriver.jit_merge_point(code=self, expression=self.body, environment=env)
                        result = self.body.evaluate(env)
                        assert result is None
                    except BreakException:
                        break

                env.pop()

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            Parser('let var a := 0 in a end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[InternalMergePointFor(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                                                 body=Assign(lvalue=LValue(name='a', next=None),
                                                                             expression=Subtract(
                                                                                 left=LValue(name='a', next=None),
                                                                                 right=LValue(name='i',
                                                                                              next=None)))),
                                           LValue(name='a', next=None)])])
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    def test_merge_point_at_the_top_of_the_loop(self):
        """
        If, unlike test_merge_point_in_the_middle_of_a_block, we place the merge point at the top of the RPython while
        loop we seem to get the same result in terms of operations and blackhole interpretation:

        # Loop 1 (InternalMergePointFor(var=i, start=IntegerValue(1), end=IntegerValue(9), body=Assign(lvalue=LValue(nam
        e=a, next=None), expression=Subtract(left=LValue(name=a, next=None), right=LValue(name=i, next=None))))) : loop
        with 110 ops
        """

        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        class InternalMergePointFor(For):
            """
            This is the original implementation of a Tiger for-loop (i.e. no while conversion)
            """
            _immutable_ = True

            def evaluate(self, env):
                env.push()
                start_value = self.start.evaluate(env)
                assert isinstance(start_value, IntegerValue)
                end_value = self.end.evaluate(env)
                assert isinstance(end_value, IntegerValue)

                iterator = IntegerValue(start_value.integer)
                for i in range(iterator.integer, end_value.integer + 1):
                    jitdriver.jit_merge_point(code=self, expression=self.body, environment=env)
                    iterator.integer = i
                    env.set_current_level(self.var, iterator)
                    try:
                        result = self.body.evaluate(env)
                        assert result is None
                    except BreakException:
                        break

                env.pop()

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            Parser('let var a := 0 in a end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[InternalMergePointFor(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                                                 body=Assign(lvalue=LValue(name='a', next=None),
                                                                             expression=Subtract(
                                                                                 left=LValue(name='a', next=None),
                                                                                 right=LValue(name='i',
                                                                                              next=None)))),
                                           LValue(name='a', next=None)])])
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    def test_using_a_while_loop_to_avoid_range_calls(self):
        """
        Implementing the for-loop using while and avoiding the use of range yields:

        # Loop 1 (WhileImplementedFor(var=i, start=IntegerValue(1), end=IntegerValue(9), body=Assign(lvalue=LValue(name=
        a, next=None), expression=Subtract(left=LValue(name=a, next=None), right=LValue(name=i, next=None))))) :
        loop with 108 ops

        Not much better number-wise but no calls are made to range functions
        """

        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        class WhileImplementedFor(For):
            _immutable_ = True

            def evaluate(self, env):
                env.push()
                start_value = self.start.evaluate(env)
                assert isinstance(start_value, IntegerValue)
                end_value = self.end.evaluate(env)
                assert isinstance(end_value, IntegerValue)

                iterator = IntegerValue(start_value.integer)
                result = None
                while iterator.integer < end_value.integer + 1:
                    jitdriver.jit_merge_point(code=self, expression=self.body, environment=env)
                    promote(end_value)
                    env.set_current_level(self.var, iterator)

                    try:
                        result = self.body.evaluate(env)
                        assert result is None
                    except BreakException:
                        break

                    iterator.integer += 1

                env.pop()

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            Parser('let var a := 0 in a end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[WhileImplementedFor(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                                               body=Assign(lvalue=LValue(name='a', next=None),
                                                                           expression=Subtract(
                                                                               left=LValue(name='a', next=None),
                                                                               right=LValue(name='i',
                                                                                            next=None)))),
                                           LValue(name='a', next=None)])])
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    @unittest.skip("re-enable when we can ensure that the EnvironmentLevel arrays are not modified")
    def test_virtualized_for_loop_changed_merge_point_with_virtualizable(self):
        """
        This attempts to virtualize the values stored in an EnvironmentLevel by overwriting its construction; however,
        we cannot virtualize 'expressions[*]' because it can be resized at runtime and therefore RPython sees it as a
        list, not an array. The easy fix is to lock the environment size to the known function parameters or let
        let declarations.

        RPython's exception message:

        The virtualizable field 'inst_expressions' is not an array (found <GcStruct list { length, items }>). It usually means that you must try harder to ensure that the list is not resized at run-time. You can do that by using rpython.rlib.debug.make_sure_not_resized().

        I then tried to force the issue by using make_sure_not_resized but got:

        [annrpython:WARNING] make_sure_not_resized called, but has no effect since list_comprehension is off
        """

        def get_location(code, exp, env, it, end):
            return "%s" % code.to_string()

        # requires enabling _virtualizable_ in EnvironmentLevel
        EnvironmentLevel._virtualizable_ = ['parent', 'bindings', 'expressions[*]']

        # and trying to make sure the 'expressions' are not resized
        from rpython.rlib.debug import make_sure_not_resized

        def new_init(self, parent):
            self.parent = parent
            self.bindings = {}  # map of names to indices
            self.expressions = []  # indexed expressions
            make_sure_not_resized(self.expressions)

        EnvironmentLevel.__init__ = new_init

        jitdriver = JitDriver(greens=['code', 'expression', 'environment', 'iterator', 'end_value'], reds=['level'],
                              virtualizables=['level'], get_printable_location=get_location)

        class VirtualizedFor(For):
            _immutable_ = True

            def evaluate(self, env):
                env.push()
                start_value = self.start.evaluate(env)
                assert isinstance(start_value, IntegerValue)
                end_value = self.end.evaluate(env)
                assert isinstance(end_value, IntegerValue)

                iterator = IntegerValue(start_value.integer)
                result = None
                while iterator.integer < end_value.integer + 1:
                    jitdriver.jit_merge_point(code=self, expression=self.body, environment=env, iterator=iterator,
                                              end_value=end_value, level=env.local_variables)
                    promote(end_value)
                    env.set_current_level(self.var, iterator)

                    try:
                        result = self.body.evaluate(env)
                        assert result is None
                    except BreakException:
                        break

                    iterator.integer += 1

                env.pop()

        def test():
            # adding this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes which reduces the number of operations
            Parser('let var a := 0 in a end').parse()

            program = Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                          expressions=[Sequence(
                              expressions=[VirtualizedFor(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                                          body=Assign(lvalue=LValue(name='a', next=None),
                                                                      expression=Subtract(
                                                                          left=LValue(name='a', next=None),
                                                                          right=LValue(name='i',
                                                                                       next=None)))),
                                           LValue(name='a', next=None)])])
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)

    @unittest.skip(
        "skip until we can reconcile SimpleEnvironment with Environment; Rpython complains about return types for __locate__; perhaps descend from a different base class?")
    def test_with_a_simpler_environment(self):
        class SimpleEnvironment(Environment):
            _immutable_ = True

            def __init__(self, names=None, values=None):
                self.names = names or {}
                self.values = values or []

            @elidable
            def __locate__(self, name, level=None):
                if name not in self.names:
                    index = len(self.names)
                    self.names[name] = index
                    if index >= len(self.values):
                        self.values.append(None)
                return self.names[name]

            def push(self):
                """Create a new environment level (i.e. frame)"""
                pass

            def pop(self):
                """Remove and forget the topmost environment level (i.e. frame)"""
                pass

            @unroll_safe
            def set(self, name, expression, level=None):
                """
                Set 'name' to 'expression'; if it exists in a prior level, modify it there; otherwise, add it to the current
                level
                """
                index = self.__locate__(name)
                num_values = len(self.values)
                if index > num_values:
                    raise IndexError("index is more than one offset away from values array")
                if index == num_values:
                    self.values.append(expression)
                else:
                    self.values[index] = expression

            def set_current_level(self, name, expression, level=None):
                """Set 'name' to 'expression' only in the current level; if it exists, modify it; otherwise, add it"""
                return self.set(name, expression)

            @unroll_safe
            def get(self, name, level=None):
                """Retrieve 'name' from the environment stack by searching through all levels"""
                index = self.__locate__(name)
                return self.values[index]

            def unset(self, name, stack=None):
                """Unset 'name' only in the current level; will not search through the entire environment"""
                pass

            def size(self, level=None):
                """Non-optimized convenience method; count the number of unique names in the entire environment"""
                return len(self.names)

            def clone(self):
                """Clone an environment by copying the stack (note that the levels will only be copied shallowly so fix() may
                be necessary so the levels are immune to updates from other sources)"""
                names = {}  # can't use dict(...), only {}, in RPython
                for k in self.names:
                    names[k] = self.names[k]
                return SimpleEnvironment(names, list(self.values))

            def fix(self):
                """Collapse all of the levels into one to fix the current global display; this has the theoretical benefit of
                making clone() faster since only a 1-item list is copied. In other words, using fix() assumes that a function
                will be declared once (fixed) and called many times (clone)"""
                pass

        def test():
            create_environment_with_natives()
            program = Parser("let var a := 0 in (for i := 1 to 9 do a := a - i; a) end").parse()
            environment = SimpleEnvironment()
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(interpretation_mechanisms.meta_interpret(test, []), -45)


if __name__ == '__main__':
    unittest.main()
