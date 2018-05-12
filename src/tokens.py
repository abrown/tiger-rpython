from src.rpythonized_object import RPythonizedObject


class Token(RPythonizedObject):
    def __init__(self, value=None, location=None):
        self.value = value
        self.location = location

    def equals(self, other):
        return RPythonizedObject.equals(self, other) and self.value == other.value
        # TODO may be more honest to compare locations as well

    def to_string(self):
        return "%s%s at %s" % (self.__class__.__name__, "=" + self.value if self.value else "", self.location)


class EofToken(Token):
    pass


class EolToken(Token):
    pass


class NumberToken(Token):
    pass


class IdentifierToken(Token):
    pass


class KeywordToken(Token):
    pass


class SymbolToken(Token):
    pass


class StringToken(Token):
    pass
