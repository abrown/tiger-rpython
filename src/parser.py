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
        self.remembered = []

    def parse(self):
        return self.expression()

    def expression(self):
        exp = self.expression_without_precedence()
        if exp is None:
            raise ParseError('Unable to parse', self.next_or_remembered())
        return self.expression_with_precedence(exp)

    def expression_without_precedence(self):
        token = self.next_or_remembered()
        if self.accept(token, KeywordToken('nil')):
            return NilValue()
        elif self.accept(token, NumberToken):
            return IntegerValue(token.value)
        elif self.accept(token, StringToken):
            return StringValue(token.value)
        elif self.accept_and_remember(token, SymbolToken('(')):
            return self.sequence()
        elif self.accept_and_remember(token, IdentifierToken):
            return self.id_started()
        elif self.accept_and_remember(token, KeywordToken('new')):
            return self.object()
        elif self.accept_and_remember(token, KeywordToken('if')):
            return self.if_then()
        elif self.accept_and_remember(token, KeywordToken('while')):
            return self.while_do()
        elif self.accept_and_remember(token, KeywordToken('for')):
            return self.for_do()
        elif self.accept(token, KeywordToken('break')):
            return Break()
        elif self.accept_and_remember(token, KeywordToken('let')):
            return self.let()
        elif self.accept_and_remember(token, KeywordToken('type')):
            return self.type_declaration()
        elif self.accept_and_remember(token, KeywordToken('var')):
            return self.variable_declaration()
        elif self.accept_and_remember(token, KeywordToken('function')):
            return self.function_declaration()
        else:
            self.remember(token)
            raise None

    def expression_with_precedence(self, left, precedence=0):
        token = self.next_or_remembered()
        while self.is_operator(token) and self.precedence(token) >= precedence:
            operation = token.value
            inner_precedence = PRECEDENCE[token.value]
            right = self.expression_without_precedence()
            token = self.next_or_remembered()
            while self.is_operator(token) and self.precedence(token) > inner_precedence:
                self.remember(token)
                right = self.expression_with_precedence(right, PRECEDENCE[token.value])
                token = self.next_or_remembered()
            left = self.operation(operation, left, right)
        self.remember(token)
        return left

    def is_operator(self, token):
        return isinstance(token, SymbolToken) and token.value in PRECEDENCE

    def precedence(self, token):
        return PRECEDENCE[token.value]

    def operation(self, operation, left, right):
        operator_class = OPERATORS[operation]  # TODO probably will not work in RPython
        return operator_class(left, right)

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
                token = self.next_or_remembered()
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

    def if_then(self):
        self.expect(self.next_or_remembered(), KeywordToken('if'))
        condition = self.expression()
        self.expect(self.next_or_remembered(), KeywordToken('then'))
        exp1 = self.expression()
        exp2 = None
        if self.accept(self.next(), KeywordToken('else')):
            exp2 = self.expression()
        return If(condition, exp1, exp2)

    def while_do(self):
        self.expect(self.next_or_remembered(), KeywordToken('while'))
        condition = self.expression()
        self.expect(self.next_or_remembered(), KeywordToken('do'))
        body = self.expression()
        return While(condition, body)

    def for_do(self):
        self.expect(self.next_or_remembered(), KeywordToken('for'))
        var = self.expect(self.next_or_remembered(), IdentifierToken)
        self.expect(self.next_or_remembered(), SymbolToken(':='))
        start = self.expression()
        self.expect(self.next_or_remembered(), KeywordToken('to'))
        end = self.expression()
        self.expect(self.next_or_remembered(), KeywordToken('do'))
        body = self.expression()
        return For(var.value, start, end, body)

    def let(self):
        self.expect(self.next_or_remembered(), KeywordToken('let'))
        decs = self.decs()
        self.expect(self.next_or_remembered(), KeywordToken('in'))
        exps = self.exps()
        self.expect(self.next_or_remembered(), KeywordToken('end'))
        return Let(decs, exps)

    def decs(self):
        pass

    def exps(self):
        expressions = [self.expression()]
        while self.accept(self.next_or_remembered(), SymbolToken(';')):
            expressions.append(self.expression())
        return expressions

    def declaration(self):
        token = self.next_or_remembered()
        if self.accept_and_remember(token, KeywordToken):
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
            self.remember(token)
        return None

    def type_declaration(self):
        self.expect(self.next_or_remembered(), KeywordToken('type'))
        id = self.expect_id(self.next_or_remembered())
        self.expect(self.next(), SymbolToken('='))
        ty = self.type()
        return TypeDeclaration(id, ty)

    def type(self):
        token = self.next_or_remembered()
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
        self.expect(self.next_or_remembered(), KeywordToken('var'))
        id = self.expect_id(self.next_or_remembered())
        token = self.next_or_remembered()
        type_id = None
        if self.accept(token, SymbolToken(':')):
            type_id = self.type()
            token = self.next()
        self.expect(token, SymbolToken(':='))
        exp = self.expression()
        return VariableDeclaration(id, type_id, exp)

    def type_fields(self):
        token = self.next_or_remembered()
        if self.accept_and_remember(token, IdentifierToken):
            type_fields = {}
            name, type_id = self.type_field()
            type_fields[name] = type_id
            token = self.next_or_remembered()
            while self.accept(token, SymbolToken(',')):
                name, type_id = self.type_field()
                type_fields[name] = type_id
                token = self.next_or_remembered()
            self.remember(token)
            return type_fields
        else:
            self.remember(token)
            return {}

    def type_field(self):
        id = self.expect_id(self.next_or_remembered())
        self.expect(self.next_or_remembered(), SymbolToken(':'))
        type = self.type_id()
        return id, type

    def type_id(self):
        return TypeId(self.expect(self.next_or_remembered(), IdentifierToken).value)

    def function_declaration(self):
        self.expect(self.next_or_remembered(), KeywordToken('function'))
        id = self.expect_id(self.next_or_remembered())
        self.expect(self.next_or_remembered(), SymbolToken('('))
        params = self.type_fields()
        self.expect(self.next_or_remembered(), SymbolToken(')'))
        token = self.next_or_remembered()
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
        self.expect(self.next_or_remembered(), SymbolToken('('))
        token = self.next_or_remembered()
        if token != SymbolToken(')'):
            self.remember(token)
            exp = self.expression()
            exps.append(exp)
            token = self.next_or_remembered()
            while self.accept(token, SymbolToken(';')):
                exp = self.expression()
                exps.append(exp)
                token = self.next_or_remembered()
        self.expect(token, SymbolToken(')'))
        return Sequence(exps)

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

    def expect_id(self, token):
        return self.expect(token, IdentifierToken).value
