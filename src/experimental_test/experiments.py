import unittest

from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rtyper.llinterp import LLInterpreter
from rpython.translator.interactive import Translation

from src.ast import *
from src.environment import EnvironmentLevel
from src.main.util import create_environment_with_natives
from src.parser import Parser

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
        """Interpret the function three different ways; NOTE: remember that printing out jitcodes is only available
        when 'verbose = True' is set in rpython/jit/metainterp/warmspot.py"""
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

    def test_merge_point_placement(self):
        def get_location(x):
            # return "x=%d, y=%d" % (x, y)
            return "x=%d" % x

        jitdriver = JitDriver(greens=['x'], reds=['y'], get_printable_location=get_location)

        def test():
            x = 1
            y = 0
            while True:
                # jitdriver.jit_merge_point(x=x, y=y)
                if x % 10 == 0:
                    y += 2
                    # jitdriver.can_enter_jit(x=x, y=y)
                    jitdriver.jit_merge_point(x=x, y=y)
                    y = promote(y)
                    if y >= 100:
                        y = 0
                        x += 1
                elif x >= 100:
                    break
                else:
                    x += 1
            return x

        self.assertEqual(self.meta_interpret(test, []), 101)

    def test_merge_point_placement_in_jitcodes(self):
        def get_location(a):
            return "%d" % a

        jitdriver = JitDriver(greens=['a'], reds=['b', 'c'], get_printable_location=get_location)

        def test_no_merge_point(a):
            b = a * 3
            c = b
            while b > 0:
                b -= 1
                c += 3
            return c

        def test_merge_point(a):
            b = a * 3
            c = b
            while b > 0:
                b -= 1
                c += 3
                jitdriver.jit_merge_point(a=a, b=b, c=c)
            return c

        def test_can_enter_jit(a):
            b = a * 3
            c = b
            while b > 0:
                b -= 1
                c += 3
                jitdriver.jit_merge_point(a=a, b=b, c=c)
                if c > 10:
                    pass
                    # jitdriver.can_enter_jit(a=a, b=b, c=c)
            return c

        # self.assertEqual(self.interpret_as_jitcode(test_no_merge_point, [5]), 60)
        # self.assertEqual(self.meta_interpret(test_no_merge_point, [5]), 60)
        # self.assertEqual(self.meta_interpret(test_merge_point, [5]), 60)
        self.assertEqual(self.meta_interpret(test_can_enter_jit, [5]), 60)

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
        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_for_loop_no_parser(self):
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

        self.assertEqual(test(), -45)

        # not using the parser is what causes this (and below test_virtualized_for_loop) to optimize to 31 operations, not 18/15
        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_for_loop_no_parser_with_separate_function(self):
        # both @dont_look_inside and @loop_invariant do not seem to have an effect on the 31 operations
        def parse():
            # this line creates more jitcodes in /tmp/usession-exploration-abrown/jitcodes (127 vs 50 without it) and this reduces the operations from 31 to 15
            Parser('let var a := 0 in a end').parse()

            return Let(declarations=[VariableDeclaration(name='a', type=None, exp=IntegerValue(0))],
                       expressions=[Sequence(
                           expressions=[For(var='i', start=IntegerValue(1), end=IntegerValue(9),
                                            body=Assign(lvalue=LValue(name='a', next=None),
                                                        expression=Subtract(
                                                            left=LValue(name='a', next=None),
                                                            right=LValue(name='i',
                                                                         next=None)))),
                                        LValue(name='a', next=None)])])

        def test():
            program = parse()
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(test(), -45)

        # not using the parser is what causes this (and below test_virtualized_for_loop) to optimize to 31 operations, not 18/15
        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_virtualized_for_loop(self):
        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        # adding this in brings the number of operations down from 105 to 31... still not 18
        def loop(code, expression, environment):
            jitdriver.jit_merge_point(code=code, expression=expression, environment=environment)
            return expression.evaluate(environment)

        class VirtualizedFor(For):
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

        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_virtualized_for_loop_no_loop_function(self):
        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

        class VirtualizedFor(For):
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
                        # note the inline merge point, promotions have no effect
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

        # the test will output many lines of 'bh: ...' logging at the end (see https://morepypy.blogspot.com/2010/06/blackhole-interpreter.html for more info)
        # this is due to the trace failing a guard at some point and the meta-interpreter invoking the blackhole interpreter to get out of jitcode-land
        # and the optimized trace is 73 operations long
        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_virtualized_for_loop_changed_merge_point(self):
        def get_location(code, exp, env):
            return "%s" % code.to_string()

        jitdriver = JitDriver(greens=['code', 'expression', 'environment'], reds='auto',
                              get_printable_location=get_location)

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

        # the test will output many lines of 'bh: ...' logging at the end (see https://morepypy.blogspot.com/2010/06/blackhole-interpreter.html for more info)
        # this is due to the trace failing a guard at some point and the meta-interpreter invoking the blackhole interpreter to get out of jitcode-land
        # and the optimized trace is 73 operations long
        # now 90+ long
        # loop with 57 ops once Parser.parse is added back in to create more jitcodes
        # avoiding the hint(iterator, virtualizable) brings it down to 56 ops
        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_virtualized_for_loop_changed_merge_point_with_virtualizable(self):
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

        # however, cannot virtualize 'expressions[*]' because it can be resized at runtime and therefore RPython sees it as a list, not an array
        # i.e. Exception: The virtualizable field 'inst_expressions' is not an array (found <GcStruct list { length, items }>). It usually means that you must try harder to ensure that the list is not resized at run-time. You can do that by using rpython.rlib.debug.make_sure_not_resized().
        # tried using make_sure_not_resized but got: [annrpython:WARNING] make_sure_not_resized called, but has no effect since list_comprehension is off

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

        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_for_loop_no_with_simple_environment(self):
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

        # the test will output many lines of 'bh: ...' logging at the end (see https://morepypy.blogspot.com/2010/06/blackhole-interpreter.html for more info)
        # this is due to the trace failing a guard at some point and the meta-interpreter invoking the blackhole interpreter to get out of jitcode-land
        # and the optimized trace is 73 operations long
        # self.assertEqual(self.interpret_in_python(test, []), -45)
        # self.translate_to_graph(test, [])
        self.assertEqual(self.meta_interpret(test, []), -45)

    def test_while_loop_changed_merge_point(self):
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

        self.assertEqual(self.meta_interpret(test, []), 100)

    def test_nested_while_loops(self):
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
            program = Parser("""
            let var a := 0 var b := 0 in 
                while a < 100 do
                   (a := a + 1;
                   while b < 100 do
                       (b := b + 1);
                    b := 0
                   )
            end""").parse()

            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(self.meta_interpret(test, []), 100)


if __name__ == '__main__':
    unittest.main()
