from src.ast import NilValue, IntegerValue, StringValue, ArrayCreation, TypeId, RecordCreation, LValue, \
    ObjectCreation, FunctionCall, RecordLValue, ArrayLValue, Assign, If, While, For, Break, Let, \
    TypeDeclaration, ArrayType, VariableDeclaration, FunctionDeclaration, RecordType, Sequence, Multiply, Divide, Add, \
    Subtract, GreaterThanOrEquals, LessThanOrEquals, Equals, NotEquals, GreaterThan, LessThan, \
    And, Or
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


PRECEDENCE = {
    '*': 5,
    '/': 5,
    '+': 4,
    '-': 4,
    '>=': 3,
    '<=': 3,
    '=': 3,
    '<>': 3,
    '>': 3,
    '<': 3,
    '&': 2,
    '|': 1,
}

OPERATORS = {
    '*': Multiply,
    '/': Divide,
    '+': Add,
    '-': Subtract,
    '>=': GreaterThanOrEquals,
    '<=': LessThanOrEquals,
    '=': Equals,
    '<>': NotEquals,
    '>': GreaterThan,
    '<': LessThan,
    '&': And,
    '|': Or
}


class Parser:
    def __init__(self, text):
        self.tokenizer = Tokenizer(text)

    def parse(self):
        return self.expression()

    def expression(self):
        exp = self.expression_without_precedence()
        if exp is None:
            raise ParseError('Unable to parse', self.peek())
        return self.expression_with_precedence(exp)

    def expression_without_precedence(self):
        if self.has_next(KeywordToken('nil')):
            return NilValue()
        elif self.has_next(NumberToken):
            token = self.next()
            return IntegerValue(token.value)
        elif self.has_next(StringToken):
            token = self.next()
            return StringValue(token.value)
        elif self.has_next(SymbolToken('(')):
            return self.sequence()
        elif self.has_next(IdentifierToken):
            return self.id_started()
        elif self.has_next(KeywordToken('new')):
            return self.object()
        elif self.has_next(KeywordToken('if')):
            return self.if_then()
        elif self.has_next(KeywordToken('while')):
            return self.while_do()
        elif self.has_next(KeywordToken('for')):
            return self.for_do()
        elif self.has_next(KeywordToken('break')):
            return Break()
        elif self.has_next(KeywordToken('let')):
            return self.let()
        elif self.has_next(KeywordToken('type')):
            return self.type_declaration()
        elif self.has_next(KeywordToken('var')):
            return self.variable_declaration()
        elif self.has_next(KeywordToken('function')):
            return self.function_declaration()
        else:
            return None

    def expression_with_precedence(self, left, precedence=0):
        """See https://en.wikipedia.org/wiki/Operator-precedence_parser"""
        token = self.peek()
        while self.is_operator(token) and self.precedence(token) >= precedence:
            self.next()  # consume operator
            operation = token.value
            inner_precedence = PRECEDENCE[token.value]
            right = self.expression_without_precedence()
            token = self.peek()
            while self.is_operator(token) and self.precedence(token) >= inner_precedence:
                right = self.expression_with_precedence(right, PRECEDENCE[token.value])
                token = self.peek()
            left = self.operation(operation, left, right)
        return left

    def is_operator(self, token):
        return isinstance(token, SymbolToken) and token.value in PRECEDENCE

    def precedence(self, token):
        return PRECEDENCE[token.value]

    def operation(self, operation, left, right):
        operator_class = OPERATORS[operation]  # TODO probably will not work in RPython
        return operator_class(left, right)

    def id_started(self):
        """An ID has been peeked above, peek further..."""
        if self.has_next(SymbolToken('{'), 1):
            return self.record()
        elif self.has_next(SymbolToken('('), 1):
            return self.function_call()
        else:
            lvalue = self.lvalue()
            return self.lvalue_started(lvalue)

    def lvalue_started(self, lvalue):
        if self.has_next(SymbolToken(':=')):
            self.next()  # discard :=
            exp = self.expression()
            return Assign(lvalue, exp)
        elif self.has_next(KeywordToken('of')):
            self.next()  # discard of
            return self.array_from_lvalue(lvalue)
        else:
            return lvalue

    def array(self):
        lvalue = self.lvalue()
        return self.array_from_lvalue(lvalue)

    def array_from_lvalue(self, lvalue):
        assert isinstance(lvalue, LValue)
        type = lvalue.name
        assert isinstance(lvalue.next, ArrayLValue)
        exp1 = lvalue.next.exp
        exp2 = self.expression()
        return ArrayCreation(TypeId(type), exp1, exp2)

    def record(self):
        type = self.expect(self.next(), IdentifierToken)
        self.expect(self.next(), SymbolToken('{'))
        fields = {}
        while self.has_next(IdentifierToken):
            id, exp = self.id_field()
            fields[id] = exp
            token2 = self.next()
            if self.accept(token2, SymbolToken(',')):
                pass
            elif self.accept(token2, SymbolToken('}')):
                break
            else:
                raise ParseError('Expected either , or }', token2)
            # TODO possibility for garbage after ', ...'
        return RecordCreation(TypeId(type.value), fields)

    def id_field(self):
        id = self.id(self.next())
        self.expect(self.next(), SymbolToken('='))
        exp = self.expression()
        return id, exp

    def object(self):
        self.expect(self.next(), KeywordToken('new'))
        type_id = self.expect(self.next(), IdentifierToken)
        return ObjectCreation(TypeId(type_id.value))

    def function_call(self):
        function_id = self.id(self.next())
        args = self.args()
        return FunctionCall(function_id, args)

    def args(self):
        self.expect(self.next(), SymbolToken('('))
        args = []
        token = self.peek()
        if token != SymbolToken(')'):
            exp = self.expression()
            args.append(exp)
            while self.has_next(SymbolToken(',')):
                self.next()  # discard ,
                exp = self.expression()
                args.append(exp)
        self.expect(self.next(), SymbolToken(')'))
        return args

    def lvalue(self):
        id = self.id(self.next())
        next = self.lvalue_next()
        return LValue(id, next)

    def lvalue_next(self):
        next = None
        if self.has_next(SymbolToken('.')):
            self.next()  # discard .
            next = self.record_lvalue()
        elif self.has_next(SymbolToken('[')):
            self.next()  # discard [
            next = self.array_lvalue()
        return next

    def record_lvalue(self):
        id = self.expect(self.next(), IdentifierToken)
        next = self.lvalue_next()
        return RecordLValue(id.value, next)

    def array_lvalue(self):
        exp = self.expression()
        self.expect(self.next(), SymbolToken(']'))
        next = self.lvalue_next()
        return ArrayLValue(exp, next)

    def if_then(self):
        self.expect(self.next(), KeywordToken('if'))
        condition = self.expression()
        self.expect(self.next(), KeywordToken('then'))
        exp1 = self.expression()
        exp2 = None
        if self.has_next(KeywordToken('else')):
            self.next()  # discard else
            exp2 = self.expression()
        return If(condition, exp1, exp2)

    def while_do(self):
        self.expect(self.next(), KeywordToken('while'))
        condition = self.expression()
        self.expect(self.next(), KeywordToken('do'))
        body = self.expression()
        return While(condition, body)

    def for_do(self):
        self.expect(self.next(), KeywordToken('for'))
        var = self.expect(self.next(), IdentifierToken)
        self.expect(self.next(), SymbolToken(':='))
        start = self.expression()
        self.expect(self.next(), KeywordToken('to'))
        end = self.expression()
        self.expect(self.next(), KeywordToken('do'))
        body = self.expression()
        return For(var.value, start, end, body)

    def let(self):
        self.expect(self.next(), KeywordToken('let'))
        decs = self.decs()
        self.expect(self.next(), KeywordToken('in'))
        exps = self.exps()
        self.expect(self.next(), KeywordToken('end'))
        return Let(decs, exps)

    def decs(self):
        pass

    def exps(self):
        expressions = [self.expression()]
        while self.accept(self.next(), SymbolToken(';')):
            expressions.append(self.expression())
        return expressions

    def declaration(self):
        if self.has_next(KeywordToken):
            token = self.peek()
            if token.value == 'type':
                return self.type_declaration()
            elif token.value == 'var':
                return self.variable_declaration()
            elif token.value == 'function':
                return self.function_declaration()
            elif token.value == 'import':
                return self.import_declaration()
            else:
                raise ExpectationError('Expected keyword in {type, class, var, function, primitive, import}', token)
        else:
            return None

    def type_declaration(self):
        self.expect(self.next(), KeywordToken('type'))
        id = self.id(self.next())
        self.expect(self.next(), SymbolToken('='))
        ty = self.type()
        return TypeDeclaration(id, ty)

    def type(self):
        token = self.next()
        if self.accept(token, IdentifierToken):
            return TypeId(token.value)
        elif self.accept(token, SymbolToken('{')):
            return RecordType(self.type_fields())
        elif self.accept(token, KeywordToken('array')):
            self.expect(self.next(), KeywordToken('of'))
            id = self.expect(self.next(), IdentifierToken)
            return ArrayType(id.value)
        else:
            raise ExpectationError('Expected a type definition', token)

    def variable_declaration(self):
        self.expect(self.next(), KeywordToken('var'))
        id = self.id(self.next())
        token = self.next()
        type_id = None
        if self.accept(token, SymbolToken(':')):
            type_id = self.type()
            token = self.next()
        self.expect(token, SymbolToken(':='))
        exp = self.expression()
        return VariableDeclaration(id, type_id, exp)

    def type_fields(self):
        if self.has_next(IdentifierToken):
            type_fields = {}
            name, type_id = self.type_field()
            type_fields[name] = type_id
            while self.has_next(SymbolToken(',')):
                self.next()  # discard ,
                name, type_id = self.type_field()
                type_fields[name] = type_id
            return type_fields
        else:
            return {}

    def type_field(self):
        id = self.id(self.next())
        self.expect(self.next(), SymbolToken(':'))
        type = self.type_id()
        return id, type

    def type_id(self):
        type_id = self.expect(self.next(), IdentifierToken)
        return TypeId(type_id.value)

    def function_declaration(self):
        self.expect(self.next(), KeywordToken('function'))
        id = self.id(self.next())
        self.expect(self.next(), SymbolToken('('))
        params = self.type_fields()
        self.expect(self.next(), SymbolToken(')'))
        token = self.next()
        return_type = None
        if self.accept(token, SymbolToken(':')):
            return_type = self.type()
            token = self.next()
        self.expect(token, SymbolToken('='))
        exp = self.expression()
        return FunctionDeclaration(id, params, return_type, exp)

    def import_declaration(self):
        raise NotImplementedError

    def sequence(self):
        exps = []
        self.expect(self.next(), SymbolToken('('))
        if self.peek() != SymbolToken(')'):
            exp = self.expression()
            exps.append(exp)
            while self.has_next(SymbolToken(';')):
                self.next()  # discard ;
                exp = self.expression()
                exps.append(exp)
        self.expect(self.next(), SymbolToken(')'))
        return Sequence(exps)

    def id(self, token):
        return self.expect(token, IdentifierToken).value

    # navigation methods TODO make private

    def peek(self):
        return self.tokenizer.peek()

    def next(self):
        """Return the next token"""
        return self.tokenizer.next()

    def has_next(self, expected, index=0):
        """Check if the next token (peeked at, not consumed) is of a certain type or has a certain value"""
        token = self.tokenizer.peek(index)
        return self.accept(token, expected)

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

