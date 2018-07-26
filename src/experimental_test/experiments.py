import unittest

from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rtyper.llinterp import LLInterpreter
from rpython.translator.interactive import Translation

from src.ast import *
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
            program = Parser("let var a := 0 in (for i := 1 to 9 do a := a - i; a) end").parse()
            print program
            environment = create_environment_with_natives()  # apparently RPython barfs if we just use Environment() here because NativeFunctionDeclaration.__init__ is never called so the flowspace does not know about the 'function' field
            result = program.evaluate(environment)
            assert isinstance(result, IntegerValue)
            return result.integer

        self.assertEqual(test(), -45)

        # 280+ operations
        # self.assertEqual(self.interpret_as_jitcode(test, []), 45)

        # 18 operations: the stderr trace of this looks almost exactly like the binary-run version (but has additional guard_nonnull_class checks, GcStruct fields)
        # 15 operations: adding @unroll_safe to LValue.evaluate cuts some operations; Envinronment.get reduces down to getfield_gc_r of list.items, getarrayitem_gc_r from this array, getfield_gc_i from integerValue.integer
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


if __name__ == '__main__':
    unittest.main()
