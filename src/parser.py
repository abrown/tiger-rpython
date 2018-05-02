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
        # TODO should this be self.exps()?
        return self.expression()

    def expression(self):
        exp = self.expression_without_precedence()
        if exp is None:
            raise ParseError('Unable to parse', self.peek())
        return self.expression_with_precedence(exp)

    def expression_without_precedence(self):
        if self.accept(KeywordToken('nil')):
            return NilValue()
        elif self.accept(NumberToken):
            token = self.next()
            return IntegerValue(token.value)
        elif self.accept_and_consume(SymbolToken('-')):
            token = self.next()
            return IntegerValue('-' + token.value)
        elif self.accept(StringToken):
            token = self.next()
            return StringValue(token.value)
        elif self.accept(SymbolToken('(')):
            return self.sequence()
        elif self.accept(IdentifierToken):
            return self.id_started()
        elif self.accept(KeywordToken('new')):
            return self.object()
        elif self.accept(KeywordToken('if')):
            return self.if_then()
        elif self.accept(KeywordToken('while')):
            return self.while_do()
        elif self.accept(KeywordToken('for')):
            return self.for_do()
        elif self.accept(KeywordToken('break')):
            return Break()
        elif self.accept(KeywordToken('let')):
            return self.let()
        elif self.accept(KeywordToken('type')):
            return self.type_declaration()
        elif self.accept(KeywordToken('var')):
            return self.variable_declaration()
        elif self.accept(KeywordToken('function')):
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
        if self.accept(SymbolToken('{'), self.peek(1)):
            return self.record()
        elif self.accept(SymbolToken('('), self.peek(1)):
            return self.function_call()
        else:
            lvalue = self.lvalue()
            return self.lvalue_started(lvalue)

    def lvalue_started(self, lvalue):
        if self.accept_and_consume(SymbolToken(':=')):
            exp = self.expression()
            return Assign(lvalue, exp)
        elif self.accept_and_consume(KeywordToken('of')):
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
        type = self.expect(IdentifierToken)
        self.expect(SymbolToken('{'))
        fields = {}
        while self.accept(IdentifierToken):
            id, exp = self.id_field()
            fields[id] = exp
            token2 = self.next()
            if self.accept(SymbolToken(','), token2):
                pass
            elif self.accept(SymbolToken('}'), token2):
                break
            else:
                raise ParseError('Expected either , or }', token2)
            # TODO possibility for garbage after ', ...'
        return RecordCreation(TypeId(type.value), fields)

    def id_field(self):
        id = self.id()
        self.expect(SymbolToken('='))
        exp = self.expression()
        return id, exp

    def object(self):
        self.expect(KeywordToken('new'))
        type_id = self.expect(IdentifierToken)
        return ObjectCreation(TypeId(type_id.value))

    def function_call(self):
        function_id = self.id()
        args = self.args()
        return FunctionCall(function_id, args)

    def args(self):
        self.expect(SymbolToken('('))
        args = []
        token = self.peek()
        if token != SymbolToken(')'):
            exp = self.expression()
            args.append(exp)
            while self.accept_and_consume(SymbolToken(',')):
                exp = self.expression()
                args.append(exp)
        self.expect(SymbolToken(')'))
        return args

    def lvalue(self):
        id = self.id()
        next = self.lvalue_next()
        return LValue(id, next)

    def lvalue_next(self):
        next = None
        if self.accept_and_consume(SymbolToken('.')):
            next = self.record_lvalue()
        elif self.accept_and_consume(SymbolToken('[')):
            next = self.array_lvalue()
        return next

    def record_lvalue(self):
        id = self.expect(IdentifierToken)
        next = self.lvalue_next()
        return RecordLValue(id.value, next)

    def array_lvalue(self):
        exp = self.expression()
        self.expect(SymbolToken(']'))
        next = self.lvalue_next()
        return ArrayLValue(exp, next)

    def if_then(self):
        self.expect(KeywordToken('if'))
        condition = self.expression()
        self.expect(KeywordToken('then'))
        exp1 = self.expression()
        exp2 = None
        if self.accept_and_consume(KeywordToken('else')):
            exp2 = self.expression()
        return If(condition, exp1, exp2)

    def while_do(self):
        self.expect(KeywordToken('while'))
        condition = self.expression()
        self.expect(KeywordToken('do'))
        body = self.expression()
        return While(condition, body)

    def for_do(self):
        self.expect(KeywordToken('for'))
        var = self.expect(IdentifierToken)
        self.expect(SymbolToken(':='))
        start = self.expression()
        self.expect(KeywordToken('to'))
        end = self.expression()
        self.expect(KeywordToken('do'))
        body = self.expression()
        return For(var.value, start, end, body)

    def let(self):
        self.expect(KeywordToken('let'))
        decs = self.decs()
        self.expect(KeywordToken('in'))
        exps = self.exps()
        self.expect(KeywordToken('end'))
        return Let(decs, exps)

    def decs(self):
        # TODO
        pass

    def exps(self):
        expressions = [self.expression()]
        while self.accept_and_consume(SymbolToken(';')):
            expressions.append(self.expression())
        return expressions

    def declaration(self):
        if self.accept(KeywordToken):
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
        self.expect(KeywordToken('type'))
        id = self.id()
        self.expect(SymbolToken('='))
        ty = self.type()
        return TypeDeclaration(id, ty)

    def type(self):
        token = self.next()
        if self.accept(IdentifierToken, token):
            return TypeId(token.value)
        elif self.accept(SymbolToken('{'), token):
            return RecordType(self.type_fields())
        elif self.accept(KeywordToken('array'), token):
            self.expect(KeywordToken('of'))
            id = self.expect(IdentifierToken)
            return ArrayType(id.value)
        else:
            raise ExpectationError('Expected a type definition', token)

    def variable_declaration(self):
        self.expect(KeywordToken('var'))
        id = self.id()
        type_id = None
        if self.accept_and_consume(SymbolToken(':')):
            type_id = self.type()
        self.expect(SymbolToken(':='))
        exp = self.expression()
        return VariableDeclaration(id, type_id, exp)

    def type_fields(self):
        if self.accept(IdentifierToken):
            type_fields = {}
            name, type_id = self.type_field()
            type_fields[name] = type_id
            while self.accept_and_consume(SymbolToken(',')):
                name, type_id = self.type_field()
                type_fields[name] = type_id
            return type_fields
        else:
            return {}

    def type_field(self):
        id = self.id()
        self.expect(SymbolToken(':'))
        type = self.type_id()
        return id, type

    def type_id(self):
        type_id = self.expect(IdentifierToken)
        return TypeId(type_id.value)

    def function_declaration(self):
        self.expect(KeywordToken('function'))
        id = self.id()
        self.expect(SymbolToken('('))
        params = self.type_fields()
        self.expect(SymbolToken(')'))
        return_type = None
        if self.accept_and_consume(SymbolToken(':')):
            return_type = self.type()
        self.expect(SymbolToken('='))
        exp = self.expression()
        return FunctionDeclaration(id, params, return_type, exp)

    def import_declaration(self):
        raise NotImplementedError

    def sequence(self):
        exps = []
        self.expect(SymbolToken('('))
        if self.peek() != SymbolToken(')'):
            exp = self.expression()
            exps.append(exp)
            while self.accept_and_consume(SymbolToken(';')):
                exp = self.expression()
                exps.append(exp)
        self.expect(SymbolToken(')'))
        return Sequence(exps)

    def id(self):
        token = self.expect(IdentifierToken)
        return token.value

    # navigation methods TODO make private

    def peek(self, index=0):
        """Peek at the next token"""
        return self.tokenizer.peek(index)

    def next(self):
        """Consume and return the next token"""
        return self.tokenizer.next()

    def accept(self, expected, token=None):
        """Check if the given token (or the next peeked token, if none is passed) is of a certain type or has a certain
        value"""
        token = token or self.tokenizer.peek()
        if (isinstance(expected, type) and isinstance(token, expected)) or expected == token:
            return True
        else:
            return False

    def accept_and_consume(self, expected):
        """Check if the next token is of a certain type or has a certain value; if it is, consume it"""
        accepted = self.accept(expected)
        if accepted:
            self.next()
        return accepted

    def expect(self, expected, token=None):
        """Demand that the next token is of the expected type (and optionally value) and throw an error otherwise"""
        token = token or self.next()
        if isinstance(expected, type) and isinstance(token, expected):
            return token
        elif expected == token:
            return token
        else:
            raise ExpectationError(expected, token)
