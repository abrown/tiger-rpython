class Program:
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __repr__(self):
        fields = []
        for key in self.__dict__:
            fields.append('%s=%s' % (key, self.__dict__[key]))
        return '%s(%s)' % (self.__class__.__name__, ', '.join(fields))


class Exp(Program):
    pass


class Declaration(Program):
    pass


class Literal(Exp):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, str(self.value))


class NilValue(Literal):
    def __init__(self):
        Literal.__init__(self, None)


class IntegerValue(Literal):
    def __init__(self, value):
        Literal.__init__(self, int(value))


class StringValue(Literal):
    pass


class Operation(Exp):
    pass


class PlusOperation(Operation):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class ArrayCreation(Exp):
    def __init__(self, type, inner, outer):
        self.outer = outer
        self.inner = inner
        self.type = type


class RecordCreation(Exp):
    def __init__(self, type, fields):
        self.type = type
        self.fields = fields


class ObjectCreation(Exp):
    def __init__(self, type):
        self.type = type


class TypeId(Declaration):
    def __init__(self, name):
        self.name = name


class LValue(Exp):
    def __init__(self, name, next=None):
        self.name = name
        self.next = next


class RecordLValue(LValue):
    pass


class ArrayLValue(LValue):
    def __init__(self, exp, next=None):
        self.exp = exp
        self.next = next


class FunctionCall(Exp):
    def __init__(self, name, args):
        self.name = name
        self.args = args


class MethodCall(Exp):
    def __init__(self, instance, name, args):
        self.instance = instance
        self.name = name
        self.args = args


class Assign(Exp):
    def __init__(self, lvalue, exp):
        self.lvalue = lvalue
        self.exp = exp


class If(Exp):
    def __init__(self, condition, body_if_true, body_if_false=None):
        self.condition = condition
        self.body_if_true = body_if_true
        self.body_if_false = body_if_false


class While(Exp):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body


class For(Exp):
    def __init__(self, var, start, end, body):
        self.var = var
        self.start = start
        self.end = end
        self.body = body


class Break(Exp):
    pass


class Let(Exp):
    def __init__(self, declarations, expressions):
        self.declarations = declarations
        self.expressions = expressions


class TypeDeclaration(Declaration):
    def __init__(self, name, type):
        self.name = name
        self.type = type


class VariableDeclaration(Declaration):
    def __init__(self, name, type, exp):
        self.name = name
        self.type = type
        self.exp = exp


class FunctionDeclaration(Declaration):
    def __init__(self, name, parameters, return_type, body):
        self.name = name
        self.parameters = parameters
        self.return_type = return_type
        self.body = body


class ArrayType(Declaration):
    def __init__(self, element_type):
        self.type_name = element_type


class RecordType(Declaration):
    def __init__(self, type_fields):
        self.type_fields = type_fields


class Sequence(Exp):
    def __init__(self, expressions):
        self.expressions = expressions


class BinaryOperation(Exp):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Multiply(BinaryOperation):
    pass


class Divide(BinaryOperation):
    pass


class Add(BinaryOperation):
    pass


class Subtract(BinaryOperation):
    pass


class GreaterThanOrEquals(BinaryOperation):
    pass


class LessThanOrEquals(BinaryOperation):
    pass


class Equals(BinaryOperation):
    pass


class NotEquals(BinaryOperation):
    pass


class GreaterThan(BinaryOperation):
    pass


class LessThan(BinaryOperation):
    pass


class And(BinaryOperation):
    pass


class Or(BinaryOperation):
    pass
