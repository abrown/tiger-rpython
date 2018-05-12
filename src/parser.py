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
    
    def to_string(self):
        return self.reason + " at token " + self.token.to_string()
        # TODO sub-class from RPythonizedObject?
    
    def __str__(self):
        return self.to_string()


class ExpectationError(ParseError):
    def __init__(self, expected, token):
        self.expected = expected
        self.token = token

    def to_string(self):
        return 'Expected %s but did not find it at %s' % (self.expected, self.token.to_string())


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

    # recursive descent parse methods (organized alphabetically)
    def arguments(self):
        self.__expect(SymbolToken('('))
        args = []
        token = self.__peek()
        if token != SymbolToken(')'):
            exp = self.expression()
            args.append(exp)
            while self.__accept_and_consume(SymbolToken(',')):
                exp = self.expression()
                args.append(exp)
        self.__expect(SymbolToken(')'))
        return args

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

    def array_lvalue(self):
        exp = self.expression()
        self.__expect(SymbolToken(']'))
        next = self.lvalue_next()
        return ArrayLValue(exp, next)

    def declaration(self):
        if self.__accept_type(KeywordToken):
            token = self.__peek()
            if token.value == 'type':
                return self.type_declaration()
            elif token.value == 'var':
                return self.variable_declaration()
            elif token.value == 'function':
                return self.function_declaration()
            elif token.value == 'import':
                return self.import_declaration()
            else:
                raise ExpectationError('keyword in {type, var, function, import}', token)
        else:
            return None

    def declarations(self):
        declarations = []
        while self.is_declaration():
            declaration = self.declaration()
            declarations.append(declaration)
        return declarations

    def expression(self):
        exp = self.expression_without_precedence()
        if exp is None:
            raise ParseError('Unable to parse', self.__peek())
        return self.expression_with_precedence(exp)

    def expressions(self):
        # note that though Dr. Appel's specification admits empty lists of expressions, I restrict this to at
        # least one expression to avoid exception handling
        expressions = [self.expression()]
        while self.__accept_and_consume(SymbolToken(';')):
            expressions.append(self.expression())
        return expressions

    def expression_with_precedence(self, left, precedence=0):
        """See https://en.wikipedia.org/wiki/Operator-precedence_parser"""
        token = self.__peek()
        while self.is_operator(token) and self.precedence(token) >= precedence:
            self.__next()  # consume operator
            operation = token.value
            inner_precedence = PRECEDENCE[token.value]
            right = self.expression_without_precedence()
            token = self.__peek()
            while self.is_operator(token) and self.precedence(token) >= inner_precedence:
                right = self.expression_with_precedence(right, PRECEDENCE[token.value])
                token = self.__peek()
            left = self.operation(operation, left, right)
        return left

    def expression_without_precedence(self):
        if self.__accept(KeywordToken('nil')):
            return NilValue()
        elif self.__accept_type(NumberToken):
            token = self.__next()
            return IntegerValue(token.value)
        elif self.__accept_and_consume(SymbolToken('-')):
            token = self.__next()
            return IntegerValue('-' + token.value)
        elif self.__accept_type(StringToken):
            token = self.__next()
            return StringValue(token.value)
        elif self.__accept(SymbolToken('(')):
            return self.sequence()
        elif self.__accept_type(IdentifierToken):
            return self.id_started()
        elif self.__accept(KeywordToken('new')):
            return self.object()
        elif self.__accept(KeywordToken('if')):
            return self.if_then()
        elif self.__accept(KeywordToken('while')):
            return self.while_do()
        elif self.__accept(KeywordToken('for')):
            return self.for_do()
        elif self.__accept(KeywordToken('break')):
            return Break()
        elif self.__accept(KeywordToken('let')):
            return self.let()
        elif self.__accept(KeywordToken('type')):
            return self.type_declaration()
        elif self.__accept(KeywordToken('var')):
            return self.variable_declaration()
        elif self.__accept(KeywordToken('function')):
            return self.function_declaration()
        else:
            return None

    def for_do(self):
        self.__expect(KeywordToken('for'))
        var = self.__expect_type(IdentifierToken)
        self.__expect(SymbolToken(':='))
        start = self.expression()
        self.__expect(KeywordToken('to'))
        end = self.expression()
        self.__expect(KeywordToken('do'))
        body = self.expression()
        return For(var.value, start, end, body)

    def function_call(self):
        function_id = self.id()
        args = self.arguments()
        return FunctionCall(function_id, args)

    def function_declaration(self):
        self.__expect(KeywordToken('function'))
        id = self.id()
        self.__expect(SymbolToken('('))
        params = self.type_fields()
        self.__expect(SymbolToken(')'))
        return_type = None
        if self.__accept_and_consume(SymbolToken(':')):
            return_type = self.type()
        self.__expect(SymbolToken('='))
        exp = self.expression()
        return FunctionDeclaration(id, params, return_type, exp)

    def id(self):
        token = self.__expect_type(IdentifierToken)
        return token.value

    def id_field(self):
        id = self.id()
        self.__expect(SymbolToken('='))
        exp = self.expression()
        return id, exp

    def id_started(self):
        """An ID has been peeked above, peek further..."""
        if self.__accept(SymbolToken('{'), self.__peek(1)):
            return self.record()
        elif self.__accept(SymbolToken('('), self.__peek(1)):
            return self.function_call()
        else:
            lvalue = self.lvalue()
            return self.lvalue_started(lvalue)

    def if_then(self):
        self.__expect(KeywordToken('if'))
        condition = self.expression()
        self.__expect(KeywordToken('then'))
        exp1 = self.expression()
        exp2 = None
        if self.__accept_and_consume(KeywordToken('else')):
            exp2 = self.expression()
        return If(condition, exp1, exp2)

    def import_declaration(self):
        raise NotImplementedError

    def is_declaration(self):
        token = self.__peek()
        return isinstance(token, KeywordToken) and token.value in ['type', 'var', 'function', 'import']

    def is_operator(self, token):
        return isinstance(token, SymbolToken) and token.value in PRECEDENCE

    def let(self):
        self.__expect(KeywordToken('let'))
        decs = self.declarations()
        self.__expect(KeywordToken('in'))
        if not self.__accept(KeywordToken('end')):
            exps = self.expressions()
        else:
            exps = []
        self.__expect(KeywordToken('end'))
        return Let(decs, exps)

    def lvalue(self):
        id = self.id()
        next = self.lvalue_next()
        return LValue(id, next)

    def lvalue_next(self):
        next = None
        if self.__accept_and_consume(SymbolToken('.')):
            next = self.record_lvalue()
        elif self.__accept_and_consume(SymbolToken('[')):
            next = self.array_lvalue()
        return next

    def lvalue_started(self, lvalue):
        if self.__accept_and_consume(SymbolToken(':=')):
            exp = self.expression()
            return Assign(lvalue, exp)
        elif self.__accept_and_consume(KeywordToken('of')):
            return self.array_from_lvalue(lvalue)
        else:
            return lvalue

    def object(self):
        self.__expect(KeywordToken('new'))
        type_id = self.__expect_type(IdentifierToken)
        return ObjectCreation(TypeId(type_id.value))

    def operation(self, operation, left, right):
        operator_class = OPERATORS[operation]  # TODO probably will not work in RPython
        return operator_class(left, right)

    def precedence(self, token):
        return PRECEDENCE[token.value]

    def record(self):
        type = self.__expect_type(IdentifierToken)
        self.__expect(SymbolToken('{'))
        fields = {}
        while self.__accept_type(IdentifierToken):
            id, exp = self.id_field()
            fields[id] = exp
            token2 = self.__next()
            if self.__accept(SymbolToken(','), token2):
                pass
            elif self.__accept(SymbolToken('}'), token2):
                break
            else:
                raise ParseError('Expected either , or }', token2)
            # TODO possibility for garbage after ', ...'
        return RecordCreation(TypeId(type.value), fields)

    def record_lvalue(self):
        id = self.__expect_type(IdentifierToken)
        next = self.lvalue_next()
        return RecordLValue(id.value, next)

    def sequence(self):
        exps = []
        self.__expect(SymbolToken('('))
        if self.__peek() != SymbolToken(')'):
            exp = self.expression()
            exps.append(exp)
            while self.__accept_and_consume(SymbolToken(';')):
                exp = self.expression()
                exps.append(exp)
        self.__expect(SymbolToken(')'))
        return Sequence(exps)

    def type(self):
        token = self.__next()
        if self.__accept_type(IdentifierToken, token):
            return TypeId(token.value)
        elif self.__accept(SymbolToken('{'), token):
            return RecordType(self.type_fields())
        elif self.__accept(KeywordToken('array'), token):
            self.__expect(KeywordToken('of'))
            id = self.__expect_type(IdentifierToken)
            return ArrayType(id.value)
        else:
            raise ExpectationError('a type definition', token)

    def type_declaration(self):
        self.__expect(KeywordToken('type'))
        id = self.id()
        self.__expect(SymbolToken('='))
        ty = self.type()
        return TypeDeclaration(id, ty)

    def type_fields(self):
        if self.__accept_type(IdentifierToken):
            type_fields = {}
            name, type_id = self.type_field()
            type_fields[name] = type_id
            while self.__accept_and_consume(SymbolToken(',')):
                name, type_id = self.type_field()
                type_fields[name] = type_id
            return type_fields
        else:
            return {}

    def type_field(self):
        id = self.id()
        self.__expect(SymbolToken(':'))
        type = self.type_id()
        return id, type

    def type_id(self):
        type_id = self.__expect_type(IdentifierToken)
        return TypeId(type_id.value)

    def variable_declaration(self):
        self.__expect(KeywordToken('var'))
        id = self.id()
        type_id = None
        if self.__accept_and_consume(SymbolToken(':')):
            type_id = self.type()
        self.__expect(SymbolToken(':='))
        exp = self.expression()
        return VariableDeclaration(id, type_id, exp)

    def while_do(self):
        self.__expect(KeywordToken('while'))
        condition = self.expression()
        self.__expect(KeywordToken('do'))
        body = self.expression()
        return While(condition, body)

    # navigation methods TODO make private

    def __peek(self, index=0):
        """Peek at the next token"""
        return self.tokenizer.peek(index)

    def __next(self):
        """Consume and return the next token"""
        return self.tokenizer.next()

    def __accept(self, expected, token=None):
        """Check if the given token (or the next peeked token, if none is passed) is of a certain type or has a certain
        value"""
        token = token or self.tokenizer.peek()
        return expected.equals(token)

    def __accept_type(self, expected_type, token=None):
        """Check if the given token (or the next peeked token, if none is passed) is of a certain type or has a certain
        value"""
        # assert isinstance(expected_type, type)
        token = token or self.tokenizer.peek()
        return isinstance(token, expected_type)

    def __accept_and_consume(self, expected):
        """Check if the next token is of a certain type or has a certain value; if it is, consume it"""
        accepted = self.__accept(expected)
        if accepted:
            self.__next()
        return accepted

    def __expect(self, expected, token=None):
        """Demand that the next token is of the expected type (and optionally value) and throw an error otherwise"""
        token = token or self.__next()
        if expected.equals(token):
            return token
        else:
            raise ExpectationError(expected.to_string(), token)

    def __expect_type(self, expected_type, token=None):
        """Demand that the next token is of the expected type (and optionally value) and throw an error otherwise"""
        # assert isinstance(expected_type, type)
        token = token or self.__next()
        if isinstance(token, expected_type):
            return token
        else:
            raise ExpectationError(expected_type.__name__, token)
