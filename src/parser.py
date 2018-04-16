from src.ast import NilValue, IntegerValue, StringValue, ArrayCreation, TypeId, RecordCreation, LValue, \
    ObjectCreation, FunctionCall, RecordLValue, ArrayLValue, Assign, MethodCall
from src.tokenizer import Tokenizer
from src.tokens import NumberToken, IdentifierToken, KeywordToken, SymbolToken, StringToken


class ParseError(Exception):
    def __init__(self, reason, token):
        self.reason = reason
        self.token = token

    def __str__(self):
        return self.reason + " at token " + str(self.token)


class ExpectationError(ParseError):
    def __init__(self, expected, token):
        self.expected = expected
        self.token = token

    def __str__(self):
        return 'Expected %s but did not find it at %s' % (self.expected, self.token)


class Parser:
    def __init__(self, text):
        self.tokenizer = Tokenizer(text)
        self.remembered = []

    def parse(self):
        return self.expression()

    def expression(self):
        token = self.next_or_remembered()
        if self.accept(token, KeywordToken('nil')):
            return NilValue()
        elif self.accept(token, NumberToken):
            return IntegerValue(token.value)
        elif self.accept(token, StringToken):
            return StringValue(token.value)
        elif self.accept_and_remember(token, IdentifierToken):
            return self.id_started()
        elif self.accept_and_remember(token, KeywordToken('new')):
            return self.object()
        else:
            raise ParseError('Unable to parse', token)

    def id_started(self):
        token = self.next()
        if self.accept_and_remember(token, SymbolToken('{')):
            return self.record()
        elif self.accept_and_remember(token, SymbolToken('(')):
            return self.function_call()
        else:
            self.remember(token)
            lvalue = self.lvalue()
            return self.lvalue_started(lvalue)

    def lvalue_started(self, lvalue):
        token = self.next_or_remembered()
        if self.accept(token, SymbolToken(':=')):
            exp = self.expression()
            return Assign(lvalue, exp)
        elif self.accept_and_remember(token, SymbolToken('(')):
            return self.method_call(lvalue)
        elif self.accept_and_remember(token, KeywordToken('of')):
            return self.array_from_lvalue(lvalue)
        else:
            self.remember(token)
            return lvalue

    def array(self):
        lvalue = self.lvalue()
        return self.array_from_lvalue(lvalue)

    def array_from_lvalue(self, lvalue):
        assert isinstance(lvalue, LValue)
        type = lvalue.name
        assert isinstance(lvalue.next, ArrayLValue)
        exp1 = lvalue.next.exp
        self.expect(self.next_or_remembered(), KeywordToken('of'))
        exp2 = self.expression()
        return ArrayCreation(TypeId(type), exp1, exp2)

    def record(self):
        type = self.expect(self.next_or_remembered(), IdentifierToken)
        self.expect(self.next_or_remembered(), SymbolToken('{'))
        fields = {}
        token = self.next()
        while self.accept_and_remember(token, IdentifierToken):
            id, exp = self.id_field()
            fields[id.value] = exp
            token2 = self.next_or_remembered()
            if token2 == SymbolToken(','):
                token = self.next()
            elif token2 == SymbolToken('}'):
                break
            else:
                raise ParseError('Expected either , or }', token2)
        return RecordCreation(TypeId(type.value), fields)

    def id_field(self):
        id = self.expect(self.next_or_remembered(), IdentifierToken)
        self.expect(self.next(), SymbolToken('='))
        exp = self.expression()
        return id, exp

    def object(self):
        self.expect(self.next_or_remembered(), KeywordToken('new'))
        type_id = self.expect(self.next(), IdentifierToken)
        return ObjectCreation(TypeId(type_id.value))

    def function_call(self):
        function_id = self.expect(self.next_or_remembered(), IdentifierToken)
        args = self.args()
        return FunctionCall(function_id.value, args)

    def method_call(self, lvalue=None):
        lvalue = lvalue or self.lvalue()
        m = lvalue  # penultimate id
        n = lvalue.next  # last id
        while n is not None:
            if n.next is None:
                m.next = None
                assert isinstance(n, RecordLValue)
                break
            else:
                m = n
                n = n.next
        args = self.args()
        return MethodCall(lvalue, n.name, args)

    def args(self):
        self.expect(self.next_or_remembered(), SymbolToken('('))
        args = []
        token = self.next()
        if token != SymbolToken(')'):
            self.remember(token)
            exp = self.expression()
            args.append(exp)
            token = self.next_or_remembered()
            while token == SymbolToken(','):
                exp = self.expression()
                args.append(exp)
                token = self.next()
            self.expect(token, SymbolToken(')'))

        return args

    def lvalue(self):
        id = self.expect(self.next_or_remembered(), IdentifierToken)
        next = self.lvalue_next()
        return LValue(id.value, next)

    def lvalue_next(self):
        next = None
        token = self.next_or_remembered()
        if self.accept(token, SymbolToken('.')):
            next = self.record_lvalue()
        elif self.accept(token, SymbolToken('[')):
            next = self.array_lvalue()

        else:
            self.remember(token)
        return next

    def record_lvalue(self):
        id = self.expect(self.next_or_remembered(), IdentifierToken)
        next = self.lvalue_next()
        return RecordLValue(id.value, next)

    def array_lvalue(self):
        exp = self.expression()
        self.expect(self.next_or_remembered(), SymbolToken(']'))
        next = self.lvalue_next()
        return ArrayLValue(exp, next)

    # navigation methods TODO make private

    def next(self):
        """Return the next token"""
        return self.tokenizer.next()

    def next_or_remembered(self):
        if len(self.remembered):
            return self.remembered.pop(0)
        else:
            return self.next()

    def remember(self, token):
        self.remembered.append(token)

    def accept_and_remember(self, token, expected):
        accepted = self.accept(token, expected)
        if accepted:
            self.remember(token)
        return accepted

    def accept(self, token, expected):
        if (isinstance(expected, type) and isinstance(token, expected)) or expected == token:
            return True
        else:
            return False

    def expect(self, token, expected):
        if isinstance(expected, type) and isinstance(token, expected):
            return token
        elif expected == token:
            return token
        else:
            raise ExpectationError(expected, token)
