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


class Dec(Program):
    pass


class Literal(Exp):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, str(self.value))


class NilValue(Literal):
    def __init__(self):
        super().__init__(None)


class IntegerValue(Literal):
    def __init__(self, value):
        super().__init__(int(value))


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

class TypeId(Dec):
    def __init__(self, name):
        self.name = name

class LValue(Exp):
    def __init__(self, name):
        self.name = name