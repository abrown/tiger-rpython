class Token:
    def __init__(self, value=None, location=None):
        self.value = value
        self.location = location

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        elif self.value != other.value:
            return False
        # TODO may be more honest to compare locations as well
        else:
            return True

    def __repr__(self):
        return self.to_string()

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
