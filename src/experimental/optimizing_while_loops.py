import unittest

import interpretation_mechanisms
# Begin RPython setup; catch import errors so this can still run in CPython...
from src.ast import IntegerValue, BreakException, Let, VariableDeclaration, Sequence, LValue, Assign, While, LessThan, \
    Add
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


if __name__ == '__main__':
    unittest.main()
