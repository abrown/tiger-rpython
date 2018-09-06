from src.environment import Environment
from src.rpythonized_object import RPythonizedObject, list_equals, dict_equals, nullable_equals, list_to_string, \
    dict_to_string, nullable_to_string

# Begin RPython setup; catch import errors so this can still run in CPython...
try:
    from rpython.rlib.jit import JitDriver, elidable, promote, unroll_safe, jit_debug, we_are_jitted
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


    def jit_debug(string, arg1=0, arg2=0, arg3=0, arg4=0):
        pass


    def we_are_jitted():
        return False


def get_location(code):
    return "%s" % code.to_string()


jitdriver = JitDriver(greens=['code'], reds='auto', get_printable_location=get_location)


def jitpolicy(driver):
    try:
        from rpython.jit.codewriter.policy import JitPolicy
        return JitPolicy()
    except ImportError:
        raise NotImplemented("Abandon if we are unable to use RPython's JitPolicy")


try:
    from rpython.rlib.objectmodel import import_from_mixin
except ImportError:
    def import_from_mixin(M, special_methods=['__init__', '__del__']):
        pass


# end of RPython setup


class InterpretationError(Exception):
    def __init__(self, reason):
        self.reason = reason

    def to_string(self):
        return self.reason

    def __str__(self):
        return self.to_string()


class Program(RPythonizedObject):
    _immutable_ = True

    def evaluate(self, env):
        pass
        # TODO implement in sub-classes

    def equals(self, other):
        return RPythonizedObject.equals(self, other)
        # TODO implement in sub-classes


class Exp(Program):
    _immutable_ = True
    pass


class Declaration(Program):
    _immutable_ = True

    def __init__(self, name):
        self.name = name

    def evaluate(self, env):
        env.set_current_level(self.name, self)


class Type(Program):
    _immutable_ = True

    pass


class Value(Exp):
    _immutable_ = True

    def __init__(self):
        pass

    def value(self):
        pass

    def equals(self, other):
        return RPythonizedObject.equals(self, other)

    def evaluate(self, env):
        return self


class NilValue(Value):
    _immutable_ = True

    def __init__(self):
        Value.__init__(self)

    def value(self):
        return None

    def to_string(self):
        return '%s' % (self.__class__.__name__,)


class IntegerValue(Value):
    _immutable_ = True

    def __init__(self, value):
        Value.__init__(self)
        assert isinstance(value, int)
        self.integer = value

    def value(self):
        return self.integer

    @staticmethod
    def from_string(number):
        assert isinstance(number, str)
        return IntegerValue(int(number))

    def to_string(self):
        return '%s(%d)' % (self.__class__.__name__, self.integer)

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.integer == other.integer


class StringValue(Value):
    _immutable_ = True

    def __init__(self, value):
        Value.__init__(self)
        self.string = value

    def value(self):
        return self.string

    def to_string(self):
        return '%s(%s)' % (self.__class__.__name__, self.string)

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.string == other.string


class ArrayCreation(Exp):
    _immutable_ = True

    def __init__(self, type, length, initial_value):
        assert (isinstance(length, Exp))
        self.length_expression = length
        assert (isinstance(initial_value, Exp))
        self.initial_value_expression = initial_value
        assert (isinstance(type, TypeId))
        self.type_id = type

    def to_string(self):
        return '%s(initial_value=%s, length=%s, type=%s)' % (
            self.__class__.__name__, self.initial_value_expression.to_string(), self.length_expression.to_string(),
            self.type_id.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.initial_value_expression.equals(
            other.initial_value_expression) and self.length_expression.equals(
            other.length_expression) and self.type_id.equals(other.type_id)

    def evaluate(self, env):
        length = self.length_expression.evaluate(env)
        assert (isinstance(length, IntegerValue))
        initial_value = self.initial_value_expression.evaluate(env)
        assert (isinstance(initial_value, Value))
        # TODO type-check
        type = env.get(self.type_id.name, env.local_types)
        return ArrayValue(length.integer, initial_value)


class ArrayValue(Value):
    _immutable_ = True

    def __init__(self, length=0, initial_value=None):
        Value.__init__(self)
        self.length = length
        assert (isinstance(initial_value, Value) or initial_value is None)
        self.array = [initial_value] * length

    def to_string(self):
        return '%s(length=%d, array=%s)' % (self.__class__.__name__, self.length, list_to_string(self.array))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.length == other.length and list_equals(self.array,
                                                                                                     other.array)


class RecordCreation(Exp):
    _immutable_ = True

    def __init__(self, type, fields):
        assert (isinstance(type, TypeId))
        self.type_id = type
        # assert (isinstance(fields, dict))
        self.fields = fields

    def to_string(self):
        return '%s(type=%s, fields=%s)' % (
            self.__class__.__name__, self.type_id.to_string(), dict_to_string(self.fields))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.type_id.equals(other.type_id) \
               and dict_equals(self.fields, other.fields)

    def evaluate(self, env):
        type = env.get(self.type_id.name, env.local_types)
        assert (isinstance(type, RecordType))
        values = [None] * len(type.field_types)
        index = 0
        for field in type.field_types:
            value = self.fields[field].evaluate(env)
            values[index] = value
            index += 1
        assert (len(type.field_types) == len(values))
        return RecordValue(type, values)


class RecordValue(Value):
    _immutable_ = True

    def __init__(self, type, values=None):
        Value.__init__(self)
        assert (isinstance(type, RecordType))
        self.type = type
        assert (isinstance(values, list))
        self.values = values

    def to_string(self):
        return '%s(type=%s, values=%s)' % (self.__class__.__name__, self.type.to_string(), list_to_string(self.values))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.type.equals(other.type) and list_equals(self.values,
                                                                                                      other.values)


class TypeId(Declaration):
    _immutable_ = True

    def __init__(self, name):
        Declaration.__init__(self, name)

    def to_string(self):
        return '%s(name=%s)' % (self.__class__.__name__, self.name)

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name


class LValue(Exp):
    _immutable_ = True

    def __init__(self, name, next=None):
        self.name = name
        self.next = next

    def to_string(self):
        return '%s(name=%s, next=%s)' % (
            self.__class__.__name__, self.name, nullable_to_string(self.next))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and nullable_equals(self.next, other.next)

    @unroll_safe
    def evaluate(self, env):
        lvalue = self

        # extract normal lvalue from environment
        assert (isinstance(lvalue, LValue))
        value = env.get(self.name)
        lvalue = lvalue.next

        # iterate over records and arrays
        while lvalue:
            if isinstance(lvalue, ArrayLValue):
                assert (isinstance(value, ArrayValue))
                index = lvalue.exp.evaluate(env)
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


class RecordLValue(LValue):
    _immutable_ = True
    pass


class ArrayLValue(LValue):
    _immutable_ = True

    def __init__(self, exp, next=None):
        LValue.__init__(self, None, next)
        self.exp = exp

    def to_string(self):
        return '%s(exp=%s, next=%s)' % (
            self.__class__.__name__, self.exp.to_string(), nullable_to_string(self.next))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.exp.equals(other.exp) \
               and nullable_equals(self.next, other.next)


class FunctionCall(Exp):
    _immutable_ = True

    def __init__(self, name, arguments):
        self.name = name
        assert (isinstance(arguments, list))
        self.arguments = arguments

    def to_string(self):
        return '%s(name=%s, args=%s)' % (self.__class__.__name__, self.name, list_to_string(self.arguments))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and list_equals(self.arguments, other.arguments)

    def evaluate(self, env):
        # find declaration
        declaration = env.get(self.name)
        if not declaration:
            raise InterpretationError('Could not find function %s' % self.name)
        assert (isinstance(declaration, FunctionDeclaration) or isinstance(declaration, NativeFunctionDeclaration))

        # check arguments
        if len(self.arguments) != len(declaration.parameters):
            raise InterpretationError('Incorrect number of arguments passed (%d); expected %d for function %s' % (
                len(self.arguments), len(declaration.parameters), self.name))

        # use declaration environment for function call (note: push() allows us to reuse the frame)
        frame = declaration.environment.clone()
        frame.push()

        # evaluate arguments
        value = None
        for i in range(len(self.arguments)):
            name = declaration.parameters[i].name
            value = self.arguments[i].evaluate(env)
            assert (isinstance(value, Value))
            frame.set_current_level(name, value)

        # evaluate body
        result = None
        if isinstance(declaration, FunctionDeclaration):
            result = declaration.body.evaluate(frame)
            # TODO type-check result
        elif isinstance(declaration, NativeFunctionDeclaration):
            # only one argument is allowed due to calling RPythonized functions with var-args
            if len(self.arguments) == 1:
                result = declaration.function(value)
                assert isinstance(result, Value) if result is not None else True
                # TODO type-check result
            else:
                raise InterpretationError('Only one argument allowed in native functions: %s' % self.name)
        else:
            raise InterpretationError('Unknown function type: %s' % declaration.__class__.__name__)

        return result


class Assign(Exp):
    _immutable_ = True

    def __init__(self, lvalue, expression):
        self.lvalue = lvalue
        self.expression = expression

    def to_string(self):
        return '%s(lvalue=%s, expression=%s)' % (
            self.__class__.__name__, self.lvalue.to_string(), self.expression.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.lvalue.equals(other.lvalue) and self.expression.equals(
            other.expression)

    def evaluate(self, env):
        # TODO handle other types of lvalues
        value = self.expression.evaluate(env)
        env.set(self.lvalue.name, value)


class If(Exp):
    _immutable_ = True

    def __init__(self, condition, body_if_true, body_if_false=None):
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
    _immutable_ = True

    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def to_string(self):
        return '%s(condition=%s, body=%s)' % (
            self.__class__.__name__, self.condition.to_string(), self.body.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.condition.equals(other.condition) and self.body.equals(
            other.body)

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


class For(Exp):
    _immutable_ = True

    def __init__(self, var, start, end, body):
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
        return Sequence([
            # var iterator := start
            Assign(LValue(self.var), self.start),
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

    def evaluate(self, env):
        env.push()
        self.while_expression.evaluate(env)
        env.pop()
        return None


class Break(Exp):
    _immutable_ = True

    def evaluate(self, env):
        raise BreakException()


class BreakException(Exception):
    pass


class Let(Exp):
    _immutable_ = True

    def __init__(self, declarations, expressions):
        self.declarations = declarations
        self.expressions = expressions

    def to_string(self):
        return '%s(declarations=%s, expressions=%s)' % (
            self.__class__.__name__, list_to_string(self.declarations), list_to_string(self.expressions))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) \
               and list_equals(self.declarations, other.declarations) \
               and list_equals(self.expressions, other.expressions)

    @unroll_safe
    def evaluate(self, env):
        if not env:  # not isinstance(env, Environment):
            raise InterpretationError('No environment in %s' % self.to_string())

        env.push()

        for declaration in self.declarations:
            assert isinstance(declaration, Declaration)
            declaration.evaluate(env)
        value = None
        for expression in self.expressions:
            value = expression.evaluate(env)

        env.pop()

        return value


class TypeDeclaration(Declaration):
    _immutable_ = True

    def __init__(self, name, type):
        Declaration.__init__(self, name)
        self.type = type

    def to_string(self):
        return '%s(name=%s, type=%s)' % (self.__class__.__name__, self.name, self.type.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name and self.type.equals(other.type)

    def evaluate(self, env):
        env.set_current_level(self.name, self.type, env.local_types)


class VariableDeclaration(Declaration):
    _immutable_ = True

    def __init__(self, name, type, exp):
        Declaration.__init__(self, name)
        self.type = type
        self.exp = exp

    def to_string(self):
        return '%s(name=%s, type=%s, exp=%s)' % (
            self.__class__.__name__, self.name, nullable_to_string(self.type), self.exp.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and nullable_equals(self.type, other.type) and self.exp.equals(other.exp)

    def evaluate(self, env):
        value = self.exp.evaluate(env)
        # TODO type-check
        env.set_current_level(self.name, value)


class FunctionParameter(Declaration):
    _immutable_ = True

    def __init__(self, name, type=None):
        Declaration.__init__(self, name)
        self.name = name
        assert isinstance(type, TypeId) or type is None
        self.type = type

    def to_string(self):
        return '%s(name=%s, type=%s)' % (self.__class__.__name__, self.name, nullable_to_string(self.type))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and nullable_equals(self.type, other.type)


class FunctionDeclaration(Declaration):
    _immutable_ = True

    def __init__(self, name, parameters, return_type, body, environment=None):
        Declaration.__init__(self, name)
        assert isinstance(parameters, list)
        self.parameters = parameters
        assert isinstance(return_type, TypeId) or return_type is None
        self.return_type = return_type
        assert isinstance(body, Exp)
        self.body = body
        self.environment = environment or Environment()  # to be reset when the function declaration is evaluated

    def to_string(self):
        return '%s(name=%s, parameters=%s, return_type=%s, body=%s)' % (
            self.__class__.__name__, self.name, list_to_string(self.parameters), nullable_to_string(self.return_type),
            self.body.to_string())

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and list_equals(self.parameters, other.parameters) \
               and nullable_equals(self.return_type, other.return_type) \
               and self.body.equals(other.body)

    def evaluate(self, env):
        assert (env is not None)
        env.set_current_level(self.name, self)
        self.environment = env.clone()


class NativeFunctionDeclaration(Declaration):
    _immutable_ = True

    def __init__(self, name, parameters=None, return_type=None, function_=None):
        Declaration.__init__(self, name)
        self.parameters = parameters or []
        assert isinstance(self.parameters, list)
        assert isinstance(return_type, TypeId) or return_type is None
        self.return_type = return_type
        self.function = function_
        self.environment = Environment()  # native functions cannot touch the interpreter environment

    def to_string(self):
        return '%s(name=%s, parameters=%s, return_type=%s)' % (
            self.__class__.__name__, self.name, list_to_string(self.parameters), nullable_to_string(self.return_type))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.name == other.name \
               and list_equals(self.parameters, other.parameters) \
               and nullable_equals(self.return_type, other.return_type)


class ArrayType(Type):
    _immutable_ = True

    def __init__(self, element_type):
        self.type_name = element_type

    def to_string(self):
        return '%s(type_name=%s)' % (self.__class__.__name__, self.type_name)

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.type_name == other.type_name


class RecordType(Type):
    _immutable_ = True

    def __init__(self, field_types):
        # assert (isinstance(field_types, dict))
        self.field_types = field_types
        self.field_positions = {}
        index = 0
        for field in field_types:
            self.field_positions[field] = index
            index += 1

    def to_string(self):
        _immutable_ = True
        return '%s(field_types=%s)' % (self.__class__.__name__, dict_to_string(self.field_types))

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and dict_equals(self.field_types, other.field_types)


class Sequence(Exp):
    _immutable_ = True

    def __init__(self, expressions):
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


class BinaryOperation(Exp):
    _immutable_ = True

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.left.equals(other.left) and self.right.equals(other.right)

    def to_string(self):
        return '%s(left=%s, right=%s)' % (self.__class__.__name__, self.left.to_string(), self.right.to_string())

    # TODO inline
    def evaluate_sides_to_value(self, env):
        left_value = self.left.evaluate(env)
        assert isinstance(left_value, Value)
        right_value = self.right.evaluate(env)
        assert isinstance(right_value, Value)
        return left_value, right_value

    # TODO inline
    def evaluate_sides_to_int(self, env):
        left_value = self.left.evaluate(env)
        assert isinstance(left_value, IntegerValue)
        right_value = self.right.evaluate(env)
        assert isinstance(right_value, IntegerValue)
        return left_value.integer, right_value.integer


class Multiply(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int * right_int)


class Divide(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int // right_int)


class Add(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int + right_int)


class Subtract(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(left_int - right_int)


class GreaterThanOrEquals(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int >= right_int else IntegerValue(0)


class LessThanOrEquals(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int <= right_int else IntegerValue(0)


class Equals(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left, right) = self.evaluate_sides_to_value(env)
        return IntegerValue(1) if left.equals(right) else IntegerValue(0)


class NotEquals(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left, right) = self.evaluate_sides_to_value(env)
        return IntegerValue(1) if not left.equals(right) else IntegerValue(0)


class GreaterThan(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int > right_int else IntegerValue(0)


class LessThan(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int < right_int else IntegerValue(0)


class And(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int and right_int else IntegerValue(0)


class Or(BinaryOperation):
    _immutable_ = True

    def evaluate(self, env):
        (left_int, right_int) = self.evaluate_sides_to_int(env)
        return IntegerValue(1) if left_int or right_int else IntegerValue(0)
