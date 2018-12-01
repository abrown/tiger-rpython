from src.environment import Environment
from src.rpythonized_object import RPythonizedObject, list_equals, dict_equals, nullable_equals, list_to_string, \
    dict_to_string, nullable_to_string

# Begin RPython setup; catch import errors so this can still run in CPython...
try:
    from rpython.rlib.jit import JitDriver, elidable, promote, unroll_safe, jit_debug, we_are_jitted
    from rpython.rlib.objectmodel import import_from_mixin, specialize
except ImportError:
    class JitDriver(object):
        def __init__(self, **kw): pass

        def jit_merge_point(self, **kw): pass

        def can_enter_jit(self, **kw): pass


    def elidable(func):
        return func


    def promote(x):
        return x


    def unroll_safe(func):
        return func


    def jit_debug():  # original arguments string, arg1=0, arg2=0, arg3=0, arg4=0
        pass


    def we_are_jitted():
        return False


    def import_from_mixin():  # original arguments: M, special_methods=['__init__', '__del__']
        pass


    class specialize(object):
        @staticmethod
        def argtype(n):  # original arguments: self, *args
            assert isinstance(n, int)

            def decorated_func(func):
                return func

            return decorated_func


# specialize necessary because get_location is used by two different jitdrivers passing in different types (While and
# FunctionCall); normally RPython could resolve these to Exp but this is a late-stage annotation issue and types
# cannot be changed
@specialize.argtype(0)
def get_location(code):
    return "%s" % code.to_string()


# to virtualize: jitdriver = JitDriver(greens=['code'], reds=['env', 'result', 'value'], virtualizables=['env'],
# get_printable_location=get_location)
while_jitdriver = JitDriver(greens=['code'], reds=['env', 'result', 'value'], get_printable_location=get_location)
function_jitdriver = JitDriver(greens=['code'], reds='auto', is_recursive=True,
                               get_printable_location=get_location)


def jitpolicy(driver):
    try:
        from rpython.jit.codewriter.policy import JitPolicy
        return JitPolicy()
    except ImportError:
        raise NotImplemented("Abandon if we are unable to use RPython's JitPolicy")


# end of RPython setup


class InterpretationError(Exception):
    def __init__(self, reason):
        self.reason = reason

    def to_string(self):
        return self.reason

    def __str__(self):
        return self.to_string()


class Program(RPythonizedObject):
    """
    Tiger programs have three types of AST nodes: expressions, declarations, and types
    """
    _attrs_ = []
    _immutable_fields_ = []

    #
    # def __init__(self):
    #     RPythonizedObject.__init__(self)

    def evaluate(self, env):
        pass
        # this must be implemented in sub-classes

    def equals(self, other):
        return RPythonizedObject.equals(self, other)
        # this should be implemented in sub-classes


class Exp(Program):
    _attrs_ = []
    _immutable_fields_ = []

    def __init__(self):
        Program.__init__(self)


class Declaration(Program):
    _attrs_ = ['name', 'parent', 'index']

    _immutable_fields_ = ['name', 'parent', 'index']

    def __init__(self, name, parent=None, index=0):
        Program.__init__(self)
        self.name = name
        self.parent = parent  # the enclosing Let/FunctionDeclaration AST node containing this declaration
        # TODO remove? is this really used? or move to ScopedDeclaration
        self.index = index  # the index of this declaration within all the declarations of the parent

    def evaluate(self, env):
        raise InterpretationError('Declaration evaluation must be overriden by subclasses')


class Bound(Exp):
    """
    This subclass is used for describing AST nodes that are 'bound' to their referring declaration in scopes.py
    """
    _attrs_ = ['declaration']
    _immutable_fields_ = ['declaration']

    def __init__(self, declaration):
        Exp.__init__(self)
        self.declaration = declaration

    def resolve(self):
        raise InterpretationError('Environment resolution must be overriden by subclasses')


class Type(Program):
    _attrs_ = []

    _immutable_fields_ = []

    def __init__(self):
        Program.__init__(self)


# VALUES


class Value(Exp):
    _attrs_ = []
    _immutable_fields_ = []

    def __init__(self):
        Exp.__init__(self)

    def value(self):
        # TODO remove?
        pass

    def equals(self, other):
        return isinstance(other, Value)  # RPythonizedObject.equals(self, other)

    def evaluate(self, env):
        return self


class NilValue(Value):
    _attrs_ = []

    _immutable_fields_ = []

    def __init__(self):
        Value.__init__(self)

    def value(self):
        return None

    def to_string(self):
        return '%s' % (self.__class__.__name__,)


class IntegerValue(Value):
    _attrs_ = ['integer']
    _immutable_fields_ = ['integer']

    def __init__(self, integer):
        Value.__init__(self)
        assert isinstance(integer, int)
        self.integer = integer

    def value(self):
        pass
        # return self.integer

    @staticmethod
    def from_string(number):
        assert isinstance(number, str)
        return IntegerValue(int(number))

    def to_string(self):
        return '%s(%d)' % (self.__class__.__name__, self.integer)

    def equals(self, other):
        return isinstance(other, IntegerValue) and self.integer == other.integer


class StringValue(Value):
    _attrs_ = ['string']

    _immutable_fields_ = ['string']

    def __init__(self, string):
        Value.__init__(self)
        self.string = string

    def value(self):
        return self.string

    def to_string(self):
        return '%s(%s)' % (self.__class__.__name__, self.string)

    def equals(self, other):
        return isinstance(other, self.__class__) and self.string == other.string


class ArrayValue(Value):
    _attrs_ = ['length', 'array']
    _immutable_fields_ = ['length', 'array']

    def __init__(self, length=0, initial_value=None):
        Value.__init__(self)
        self.length = length
        assert (isinstance(initial_value, Value) or initial_value is None)
        self.array = [initial_value] * length

    def to_string(self):
        return '%s(length=%d, array=%s)' % (self.__class__.__name__, self.length, list_to_string(self.array))

    def equals(self, other):
        return isinstance(other, ArrayValue) and self.length == other.length and list_equals(self.array,
                                                                                             other.array)


class RecordValue(Value):
    _attrs_ = ['type', 'values']

    _immutable_fields_ = ['type', 'values']

    def __init__(self, record_type, values=None):
        Value.__init__(self)
        assert (isinstance(record_type, RecordType))
        self.type = record_type
        assert (isinstance(values, list))
        self.values = values

    def to_string(self):
        return '%s(type=%s, values=%s)' % (self.__class__.__name__, self.type.to_string(), list_to_string(self.values))

    def equals(self, other):
        return isinstance(other, RecordValue) and self.type.equals(other.type) and list_equals(self.values,
                                                                                                      other.values)


# EXPRESSIONS: LOCATORS AND STRUCTURE


class LValue(Bound):
    _attrs_ = ['name', 'next']

    _immutable_fields_ = ['name', 'next']

    def __init__(self, name, next_lvalue=None, declaration=None):
        Bound.__init__(self, declaration)
        self.name = name
        self.next = next_lvalue

    def to_string(self):
        return '%s(name=%s, next=%s, declaration=%s)' % (
            self.__class__.__name__, self.name, nullable_to_string(self.next), nullable_to_string(self.declaration))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and nullable_equals(self.next, other.next)

    @unroll_safe
    def evaluate(self, env):
        lvalue = self

        # extract normal lvalue from environment
        env, index = self.resolve()
        value = env.get(index)

        # iterate over records and arrays
        lvalue = lvalue.next
        while lvalue:
            if isinstance(lvalue, ArrayLValue):
                assert (isinstance(value, ArrayValue))
                index = lvalue.expression.evaluate(env)
                assert (isinstance(index, IntegerValue))
                value = value.array[index.integer]
            elif isinstance(lvalue, RecordLValue):
                assert (isinstance(value, RecordValue))
                index = value.type.field_positions[lvalue.name]
                assert (isinstance(index, int))
                value = value.values[index]
            else:
                raise InterpretationError('Incorrect AST; expected an array- or record-lvalue')
            lvalue = lvalue.next

        return value

    def resolve(self):
        declaration = self.declaration
        parent = declaration.parent
        if isinstance(parent, Let):
            return parent.environment, declaration.index
        elif isinstance(parent, FunctionDeclaration):
            return parent.environment, declaration.index
        else:
            raise InterpretationError(
                'Incorrect AST; expected to resolve a parent that is a Let or FunctionDeclaration node')


class RecordLValue(LValue):
    _attrs_ = []
    _immutable_fields_ = []
    pass


class ArrayLValue(LValue):
    _attrs_ = ['name', 'next', 'expression']

    _immutable_fields_ = ['expression']

    def __init__(self, expression, next_lvalue=None):
        LValue.__init__(self, None, next_lvalue)
        self.expression = expression

    def to_string(self):
        return '%s(exp=%s, next=%s)' % (
            self.__class__.__name__, self.expression.to_string(), nullable_to_string(self.next))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.expression.equals(other.expression) \
               and nullable_equals(self.next, other.next)


class ArrayCreation(Exp):
    _attrs_ = ['length_expression', 'initial_value_expression', 'type_id']

    _immutable_fields_ = ['length_expression', 'initial_value_expression', 'type_id']

    def __init__(self, type_id, length_expression, initial_value_expression):
        Exp.__init__(self)
        assert (isinstance(length_expression, Exp))
        self.length_expression = length_expression
        assert (isinstance(initial_value_expression, Exp))
        self.initial_value_expression = initial_value_expression
        assert (isinstance(type_id, TypeId))
        self.type_id = type_id

    def to_string(self):
        return '%s(initial_value=%s, length=%s, type=%s)' % (
            self.__class__.__name__, self.initial_value_expression.to_string(), self.length_expression.to_string(),
            self.type_id.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.initial_value_expression.equals(
            other.initial_value_expression) and self.length_expression.equals(
            other.length_expression) and self.type_id.equals(other.type_id)

    @unroll_safe
    def evaluate(self, env):
        length = self.length_expression.evaluate(env)
        assert (isinstance(length, IntegerValue))
        initial_value = self.initial_value_expression.evaluate(env)
        assert (isinstance(initial_value, Value))
        # TODO type-check
        # type = env.get(self.type_id.name, env.local_types)
        return ArrayValue(length.integer, initial_value)


class RecordCreation(Exp):
    _attrs_ = ['type_id', 'fields']

    _immutable_fields_ = ['type_id', 'fields']

    def __init__(self, type_id, fields):
        Exp.__init__(self)
        assert (isinstance(type_id, TypeId))
        self.type_id = type_id
        # assert (isinstance(fields, dict))
        self.fields = fields

    def to_string(self):
        return '%s(type=%s, fields=%s)' % (
            self.__class__.__name__, self.type_id.to_string(), dict_to_string(self.fields))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.type_id.equals(other.type_id) \
               and dict_equals(self.fields, other.fields)

    @unroll_safe
    def evaluate(self, env):
        env, env_index = self.type_id.resolve()
        record_type = env.get(env_index)
        assert (isinstance(record_type, RecordType))
        values = [None] * len(record_type.field_types)
        record_index = 0
        for field in record_type.field_types:
            value = self.fields[field].evaluate(env)
            values[record_index] = value
            record_index += 1
        assert (len(record_type.field_types) == len(values))
        return RecordValue(record_type, values)


# EXPRESSIONS: STATEMENTS


class Assign(Exp):
    _attrs_ = ['lvalue', 'expression']

    _immutable_fields_ = ['lvalue', 'expression']

    def __init__(self, lvalue, expression):
        Exp.__init__(self)
        assert isinstance(lvalue, LValue)
        self.lvalue = lvalue
        self.expression = expression

    def to_string(self):
        return '%s(lvalue=%s, expression=%s)' % (
            self.__class__.__name__, self.lvalue.to_string(), self.expression.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.lvalue.equals(other.lvalue) and self.expression.equals(
            other.expression)

    @unroll_safe
    def evaluate(self, env):
        value = self.expression.evaluate(env)

        lvalue = self.lvalue
        env, index = lvalue.resolve()
        if not lvalue.next:
            # assignment to a plain lvalue
            env.set(index, value)
        else:
            # assignment to a sub-located destination
            destination = env.get(index)
            lvalue = lvalue.next

            # traverse all locators except the last one
            while lvalue and lvalue.next:
                if isinstance(lvalue, ArrayLValue):
                    assert isinstance(destination, ArrayValue)
                    index = lvalue.expression.evaluate(env)
                    assert isinstance(index, IntegerValue)
                    destination = destination.array[index.integer]
                elif isinstance(lvalue, RecordLValue):
                    assert isinstance(destination, RecordValue)
                    index = destination.type.field_positions[lvalue.name]
                    assert isinstance(index, int)
                    destination = destination.values[index]
                else:
                    raise InterpretationError('Incorrect AST; expected an array- or record-value')
                lvalue = lvalue.next

            # assign to the last locator
            if isinstance(lvalue, ArrayLValue):
                assert isinstance(destination, ArrayValue)
                index = lvalue.expression.evaluate(env)
                assert isinstance(index, IntegerValue)
                destination.array[index.integer] = value
            elif isinstance(lvalue, RecordLValue):
                assert isinstance(destination, RecordValue)
                index = destination.type.field_positions[lvalue.name]
                assert isinstance(index, int)
                destination.values[index] = value
            else:
                raise InterpretationError('Incorrect AST; expected an array- or record-value')


class Sequence(Exp):
    _attrs_ = ['expressions']

    _immutable_fields_ = ['expressions']

    def __init__(self, expressions):
        Exp.__init__(self)
        self.expressions = expressions

    def to_string(self):
        return '%s(expressions=%s)' % (self.__class__.__name__, list_to_string(self.expressions))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and list_equals(self.expressions, other.expressions)

    @unroll_safe
    def evaluate(self, env):
        value = None
        for expression in self.expressions:
            value = expression.evaluate(env)
        return value


class Let(Exp):
    _attrs_ = ['declarations', 'expressions', 'environment']

    _immutable_fields_ = ['declarations', 'expressions']  # note that the environment is not declared immutable

    def __init__(self, declarations, expressions):
        Exp.__init__(self)
        self.declarations = declarations
        self.expressions = expressions  # the body of the let-binding; a sequence of expressions
        self.environment = Environment.empty(None, len(declarations))

    def to_string(self):
        return '%s(declarations=%s, expressions=%s)' % (
            self.__class__.__name__, list_to_string(self.declarations), list_to_string(self.expressions))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) \
               and list_equals(self.declarations, other.declarations) \
               and list_equals(self.expressions, other.expressions)

    @unroll_safe
    def evaluate(self, env):
        self.environment = self.environment.push(len(self.declarations))

        for declaration in self.declarations:
            assert isinstance(declaration, Declaration)
            declaration.evaluate(self.environment)

        value = None
        for expression in self.expressions:
            value = expression.evaluate(self.environment)

        self.environment = self.environment.pop()

        return value


# EXPRESSIONS: CONTROL FLOW


class FunctionCall(Bound):
    _attrs_ = ['name', 'arguments']

    _immutable_fields_ = ['name', 'arguments']

    def __init__(self, name, arguments, declaration=None):
        Bound.__init__(self, declaration)
        self.name = name
        assert (isinstance(arguments, list))
        self.arguments = arguments

    def to_string(self):
        return '%s(name=%s, args=%s)' % (
            self.__class__.__name__, self.name, list_to_string(self.arguments))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and list_equals(self.arguments, other.arguments)

    @unroll_safe
    def evaluate(self, env):
        function_jitdriver.jit_merge_point(code=self)

        # find declaration
        # TODO declaration = self.declaration.resolve()
        declaration = self.declaration
        if not declaration:
            raise InterpretationError('Could not find function %s' % self.name)
        assert isinstance(declaration, FunctionDeclaration) or isinstance(declaration, NativeFunctionDeclaration)

        # check arguments TODO move this check to scopes.py
        if len(self.arguments) != len(declaration.parameters):
            raise InterpretationError('Incorrect number of arguments passed (%d); expected %d for function %s' % (
                len(self.arguments), len(declaration.parameters), self.name))

        # evaluate body
        result = None  # set by function return
        if isinstance(declaration, FunctionDeclaration):
            activation_environment = declaration.environment.push(len(declaration.parameters))
            # evaluate arguments
            for i in range(len(self.arguments)):
                value = self.arguments[i].evaluate(declaration.environment)
                assert (isinstance(value, Value))
                activation_environment.set(i, value)
            # call function
            declaration.environment = activation_environment
            result = declaration.body.evaluate(activation_environment)
            declaration.environment = declaration.environment.pop()
        elif isinstance(declaration, NativeFunctionDeclaration):
            # evaluate arguments (no need for an activation environment)
            values = []
            for i in range(len(self.arguments)):
                value = self.arguments[i].evaluate(env)
                assert (isinstance(value, Value))
                values.append(value)
            # call function
            result = declaration.call(values)
        else:
            raise InterpretationError('Unknown function type: %s' % declaration.__class__.__name__)

        assert isinstance(result, Value) if result is not None else True
        # TODO type-check result

        return result

    def resolve(self):
        raise InterpretationError(
            'FunctionCall does not need resolution; it operates directly on the assigned function declaration')


class If(Exp):
    _attrs_ = ['condition', 'body_if_true', 'body_if_false']

    _immutable_fields_ = ['condition', 'body_if_true', 'body_if_false']

    def __init__(self, condition, body_if_true, body_if_false=None):
        Exp.__init__(self)
        self.condition = condition
        self.body_if_true = body_if_true
        self.body_if_false = body_if_false

    def to_string(self):
        return '%s(condition=%s, body_if_true=%s, body_if_false=%s)' % (
            self.__class__.__name__, self.condition.to_string(), self.body_if_true.to_string(),
            nullable_to_string(self.body_if_false))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.condition.equals(other.condition) \
               and self.body_if_true.equals(other.body_if_true) \
               and nullable_equals(self.body_if_false, other.body_if_false)

    @unroll_safe
    def evaluate(self, env):
        condition_value = self.condition.evaluate(env)
        assert isinstance(condition_value, IntegerValue)
        result = None
        if condition_value.integer != 0:
            result = self.body_if_true.evaluate(env)
        elif self.body_if_false is not None:
            result = self.body_if_false.evaluate(env)
        return result


class While(Exp):
    _attrs_ = ['condition', 'body']

    _immutable_fields_ = ['condition', 'body']

    def __init__(self, condition, body):
        Exp.__init__(self)
        self.condition = condition
        self.body = body

    def to_string(self):
        return '%s(condition=%s, body=%s)' % (
            self.__class__.__name__, self.condition.to_string(), self.body.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.condition.equals(other.condition) and self.body.equals(
            other.body)

    def evaluate(self, env):
        result = None
        condition_value = self.condition.evaluate(env)
        assert isinstance(condition_value, IntegerValue)
        while True:  # condition_value.integer != 0:
            while_jitdriver.jit_merge_point(code=self, env=env, result=result, value=condition_value)
            # attempted 'env = promote(env)' here but this let to incorrect number of inner loops in sumprimes
            try:
                result = self.body.evaluate(env)
            except BreakException:
                break
            condition_value = self.condition.evaluate(env)

        return result


class For(Exp):
    _attrs_ = ['var', 'start', 'end', 'body', 'while_expression']

    _immutable_fields_ = ['var', 'start', 'end', 'body', 'while_expression']

    def __init__(self, var, start, end, body):
        Exp.__init__(self)
        self.var = var
        self.start = start
        self.end = end
        self.body = body

        # transform this for-loop to a while-loop in order to use the merge point in the while-loop
        self.while_expression = self.convert_to_while()

    def to_string(self):
        return '%s(var=%s, start=%s, end=%s, body=%s)' % (
            self.__class__.__name__, self.var, self.start.to_string(), self.end.to_string(), self.body.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.var == other.var and self.start.equals(
            other.start) and self.end.equals(other.end) and self.body.equals(other.body)

    def convert_to_while(self):
        # var iterator := start
        return Let([VariableDeclaration(self.var, None, self.start)], [
            # while iterator <= end:
            While(
                LessThanOrEquals(LValue(self.var), self.end),
                # do body; iterator = iterator + 1
                Sequence([
                    self.body,
                    Assign(LValue(self.var), Add(LValue(self.var), IntegerValue(1)))
                ])
            )
        ])

    @unroll_safe
    def evaluate(self, env):
        self.while_expression.evaluate(env)
        return None


class Break(Exp):
    _attrs_ = []

    _immutable_fields_ = []

    def __init__(self):
        Exp.__init__(self)

    @unroll_safe
    def evaluate(self, env):
        raise BreakException()


class BreakException(Exception):
    pass


# EXPRESSIONS: LOGICAL AND ARITHMETIC OPERATORS


class BinaryOperation(Exp):
    _attrs_ = ['left', 'right']

    _immutable_fields_ = ['left', 'right']

    def __init__(self, left, right):
        Exp.__init__(self)
        self.left = left
        self.right = right

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.left.equals(other.left) and self.right.equals(other.right)

    def to_string(self):
        return '%s(left=%s, right=%s)' % (self.__class__.__name__, self.left.to_string(), self.right.to_string())

    # TODO inline
    @unroll_safe
    def evaluate_sides_to_value(self, env):
        left_value = self.left.evaluate(env)
        assert isinstance(left_value, Value)
        right_value = self.right.evaluate(env)
        assert isinstance(right_value, Value)
        return left_value, right_value

    # TODO inline
    @unroll_safe
    def evaluate_sides_to_int(self, env):
        left_value = self.left.evaluate(env)
        assert isinstance(left_value, IntegerValue)
        right_value = self.right.evaluate(env)
        assert isinstance(right_value, IntegerValue)
        return left_value.integer, right_value.integer


class Multiply(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int * right_int)


class Divide(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int // right_int)


class Add(BinaryOperation):

    @unroll_safe
    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int + right_int)


class Subtract(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int - right_int)


class GreaterThanOrEquals(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int >= right_int else IntegerValue(0)


class LessThanOrEquals(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int <= right_int else IntegerValue(0)


class Equals(BinaryOperation):

    def evaluate(self, env):
        (left, right) = self.evaluate_sides_to_value(env)
        return IntegerValue(1) if left.equals(right) else IntegerValue(0)


class NotEquals(BinaryOperation):

    def evaluate(self, env):
        (left, right) = self.evaluate_sides_to_value(env)
        return IntegerValue(1) if not left.equals(right) else IntegerValue(0)


class GreaterThan(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int > right_int else IntegerValue(0)


class LessThan(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int < right_int else IntegerValue(0)


class And(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int and right_int else IntegerValue(0)


class Or(BinaryOperation):

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int or right_int else IntegerValue(0)


# DECLARATIONS


class TypeId(Bound):
    _attrs_ = ['name']
    _immutable_fields_ = ['name']

    def __init__(self, name, declaration=None):
        Bound.__init__(self, declaration)
        self.name = name

    def to_string(self):
        return '%s(name=%s)' % (self.__class__.__name__, self.name)

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name

    def resolve(self):
        declaration = self.declaration
        assert isinstance(declaration, TypeDeclaration)
        parent = declaration.parent
        assert isinstance(parent, Let)
        return parent.environment, declaration.index


class TypeDeclaration(Declaration):
    _attrs_ = ['type']

    _immutable_fields_ = ['type']

    def __init__(self, name, type_id_or_struct, parent=None, index=0):
        Declaration.__init__(self, name, parent, index)
        self.type = type_id_or_struct  # note that type here can be either a Type (record, array) or a TypeId

    def to_string(self):
        return '%s(name=%s, type=%s)' % (self.__class__.__name__, self.name, self.type.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name and self.type.equals(other.type)

    @unroll_safe
    def evaluate(self, env):
        env.set(self.index, self.type)


class VariableDeclaration(Declaration):
    _attrs_ = ['type', 'expression']

    _immutable_fields_ = ['type', 'expression']

    def __init__(self, name, type_id, expression, parent=None, index=0):
        Declaration.__init__(self, name, parent, index)
        assert isinstance(type_id, TypeId) or type_id is None
        self.type = type_id
        self.expression = expression

    def to_string(self):
        return '%s(name=%s, type=%s, expression=%s)' % (
            self.__class__.__name__, self.name, nullable_to_string(self.type), self.expression.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and nullable_equals(self.type, other.type) and self.expression.equals(other.expression)

    @unroll_safe
    def evaluate(self, env):
        value = self.expression.evaluate(env)
        # TODO type-check
        env.set(self.index, value)


class FunctionParameter(Declaration):
    _attrs_ = ['type']

    _immutable_fields_ = ['type']

    def __init__(self, name, type_id=None, parent=None, index=0):
        Declaration.__init__(self, name, parent, index)
        assert isinstance(type_id, TypeId) or type_id is None
        self.type = type_id

    def to_string(self):
        return '%s(name=%s, type=%s)' % (self.__class__.__name__, self.name, nullable_to_string(self.type))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and nullable_equals(self.type, other.type)


class FunctionDeclarationBase(Declaration):
    _attrs_ = ['parameters', 'return_type']
    _immutable_fields_ = ['parameters', 'return_type']

    def __init__(self, name, parameters, return_type, parent=None, index=0):
        Declaration.__init__(self, name, parent, index)
        assert isinstance(parameters, list)
        self.parameters = parameters
        assert isinstance(return_type, TypeId) or return_type is None
        self.return_type = return_type


class FunctionDeclaration(FunctionDeclarationBase):
    _attrs_ = ['body', 'environment', 'index']
    _immutable_fields_ = ['body', 'environment?', 'index']

    def __init__(self, name, parameters, return_type, body, environment=None, index=0):
        FunctionDeclarationBase.__init__(self, name, parameters, return_type)
        assert isinstance(body, Exp)
        self.body = body
        self.environment = environment or Environment.empty(None, len(
            self.parameters))  # to be reset when the function declaration is evaluated
        assert index >= 0
        self.index = index

    def to_string(self):
        return '%s(name=%s, parameters=%s, return_type=%s, body=%s)' % (
            self.__class__.__name__, self.name, list_to_string(self.parameters), nullable_to_string(self.return_type),
            self.body.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and list_equals(self.parameters, other.parameters) \
               and nullable_equals(self.return_type, other.return_type) \
               and self.body.equals(other.body)

    @unroll_safe
    def evaluate(self, env):
        env.set(self.index, self)


class NativeFunctionDeclaration(FunctionDeclarationBase):
    _attrs_ = []

    _immutable_fields_ = []

    def __init__(self, name, parameters=None, return_type=None):
        FunctionDeclarationBase.__init__(self, name, parameters or [], return_type)

    def call(self, arguments):
        raise InterpretationError('Use a subclass of NativeFunctionDeclaration that specifies the number of arguments')

    def to_string(self):
        return '%s(name=%s, parameters=%s, return_type=%s)' % (
            self.__class__.__name__, self.name, list_to_string(self.parameters), nullable_to_string(self.return_type))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and list_equals(self.parameters, other.parameters) \
               and nullable_equals(self.return_type, other.return_type)


class NativeNoArgumentFunctionDeclaration(NativeFunctionDeclaration):
    _attrs_ = ['function']

    _immutable_fields_ = ['function']

    def __init__(self, name, return_type, python_function):
        NativeFunctionDeclaration.__init__(self, name, [], return_type)
        self.function = python_function  # remember that RPython will not accept a lambda

    def call(self, arguments):
        assert len(arguments) == 0
        return self.function()


class NativeOneArgumentFunctionDeclaration(NativeFunctionDeclaration):
    _attrs_ = ['function']

    _immutable_fields_ = ['function']

    def __init__(self, name, parameters, return_type, python_function):
        NativeFunctionDeclaration.__init__(self, name, parameters, return_type)
        self.function = python_function  # remember that RPython will not accept a lambda

    def call(self, arguments):
        assert len(arguments) == 1
        return self.function(arguments[0])


class NativeTwoArgumentFunctionDeclaration(NativeFunctionDeclaration):
    _attrs_ = ['function']

    _immutable_fields_ = ['function']

    def __init__(self, name, parameters, return_type, python_function):
        NativeFunctionDeclaration.__init__(self, name, parameters, return_type)
        self.function = python_function  # remember that RPython will not accept a lambda

    def call(self, arguments):
        assert len(arguments) == 2
        return self.function(arguments[0], arguments[1])


# TYPES


class ArrayType(Type):
    _attrs_ = ['type_name']

    _immutable_fields_ = ['type_name']

    def __init__(self, element_type):
        Type.__init__(self)
        self.type_name = element_type  # TODO match names and use TypeId instead

    def to_string(self):
        return '%s(type_name=%s)' % (self.__class__.__name__, self.type_name)

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.type_name == other.type_name


class RecordType(Type):
    _attrs_ = ['field_types', 'field_positions']

    _immutable_fields_ = ['field_types', 'field_positions']

    def __init__(self, field_types):
        Type.__init__(self)
        # assert (isinstance(field_types, dict))
        self.field_types = field_types
        self.field_positions = {}
        index = 0
        for field in field_types:
            self.field_positions[field] = index
            index += 1

    def to_string(self):
        return '%s(field_types=%s)' % (self.__class__.__name__, dict_to_string(self.field_types))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and dict_equals(self.field_types, other.field_types)


def list_classes_in_file(parent_class=None):
    import sys
    import inspect
    if parent_class:
        assert inspect.isclass(parent_class)

        def class_filter(c):
            return inspect.isclass(c) and issubclass(c, Program)
    else:
        class_filter = inspect.isclass
    return inspect.getmembers(sys.modules[__name__], class_filter)


def list_arguments_of_function(func, containing_class=None):
    import inspect
    args, arglist, keywords, defaults = inspect.getargspec(func)
    assert arglist is None, "Avoid using argument lists (e.g. *args) in constructor of class %s" % containing_class
    assert keywords is None, "Avoid using keywords (e.g. **kw) in constructor of class %s" % containing_class
    return args


def inject_logging_into_evaluate_methods():
    """
    In order to avoid cluttering the AST implementation with logging calls, this function will:
    1. examine all classes in this module
    2. if the class has an 'evaluate' attribute, replace it with a wrapper to print the string representation of the
    AST node
    :return: nothing
    """
    from functools import wraps

    def wrapper(method):
        @wraps(method)
        def wrapped(*args, **kwrds):
            self = args[0]
            env = args[1]
            if env and hasattr(env, 'debug') and env.debug:
                print(self.to_string())
            return method(*args, **kwrds)

        return wrapped

    for name, klass in list_classes_in_file():
        if 'evaluate' in klass.__dict__:
            # print('Replacing evaluate method of %s' % klass)
            setattr(klass, 'evaluate', wrapper(klass.__dict__['evaluate']))


def has_init_function(klass):
    return '__init__' in klass.__dict__ and hasattr(klass.__dict__['__init__'], '__call__')


def get_init_function(klass):
    return klass.__dict__['__init__']


def add_immutable_fields(klass):
    # init_name = '__init__'
    immutable_fields_name = '_immutable_fields_'
    # if hasattr(klass, init_name) and not hasattr(klass, immutable_fields_name):
    if has_init_function(klass) and immutable_fields_name not in klass.__dict__:
        args = [arg for arg in list_arguments_of_function(get_init_function(klass), klass.__name__) if arg != 'self']
        # TODO format list-like args, e.g. 'expressions[*]'
        print('Added _immutable_fields_ to %s: %s' % (klass.__name__, args))
        setattr(klass, immutable_fields_name, args)


def add_attrs(klass):
    attrs_name = '_attrs_'
    if attrs_name not in klass.__dict__:
        if has_init_function(klass):
            args = [arg for arg in list_arguments_of_function(get_init_function(klass), klass.__name__) if
                    arg != 'self']
        else:
            args = []
        setattr(klass, attrs_name, args)
        print('Added _attrs_ to %s: %s' % (klass.__name__, args))

# fix-up all AST nodes in this file by adding RPython's _immutable_fields_ annotation
# for name, cls in list_classes_in_file(Program):
#     add_immutable_fields(cls)
#     add_attrs(cls)
