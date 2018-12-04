from collections import OrderedDict

from src.ast import NilValue, IntegerValue, StringValue, ArrayCreation, TypeId, RecordCreation, LValue, \
    FunctionCall, RecordLValue, ArrayLValue, Assign, If, While, For, Break, Let, \
    TypeDeclaration, ArrayType, VariableDeclaration, FunctionDeclaration, RecordType, Sequence, Multiply, Divide, Add, \
    Subtract, GreaterThanOrEquals, LessThanOrEquals, Equals, NotEquals, GreaterThan, LessThan, \
    And, Or, FunctionParameter
from src.scopes import transform_lvalues
from src.tokenizer import Tokenizer
from src.tokens import NumberToken, IdentifierToken, KeywordToken, SymbolToken, StringToken


class ParseError(Exception):
    def __init__(self, reason, token):
        self.reason = reason
        self.token = token

    def to_string(self):
        return self.reason + " at token " + self.token.to_string()

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
    def __init__(self, text, source_file=None):
        self.tokenizer = Tokenizer(text, source_file)

    def parse(self, native_function_declarations=None):
        expression = self.expression()
        if native_function_declarations:
            transform_lvalues(expression, native_function_declarations)
        return expression

    # recursive descent parse methods (organized alphabetically)
    def arguments(self):
        self.__expect(SymbolToken('('))
        args = []
        token = self.__peek()
        if not token.equals(SymbolToken(')')):
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
        type_name = lvalue.name
        next_lvalue = lvalue.next
        assert isinstance(next_lvalue, ArrayLValue)
        exp1 = next_lvalue.expression
        exp2 = self.expression()
        return ArrayCreation(TypeId(type_name), exp1, exp2)

    def array_lvalue(self):
        exp = self.expression()
        self.__expect(SymbolToken(']'))
        next_lvalue = self.lvalue_next()
        return ArrayLValue(exp, next_lvalue)

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
        if self.__accept_and_consume(KeywordToken('nil')):
            return NilValue()
        elif self.__accept_type(NumberToken):
            token = self.__next()
            return IntegerValue.from_string(token.value)
        elif self.__accept_and_consume(SymbolToken('-')):
            token = self.__next()
            return IntegerValue.from_string('-' + token.value)
        elif self.__accept_type(StringToken):
            token = self.__next()
            return StringValue(token.value)
        elif self.__accept(SymbolToken('(')):
            return self.sequence()
        elif self.__accept_type(IdentifierToken):
            return self.id_started()
        elif self.__accept(KeywordToken('if')):
            return self.if_then()
        elif self.__accept(KeywordToken('while')):
            return self.while_do()
        elif self.__accept(KeywordToken('for')):
            return self.for_do()
        elif self.__accept_and_consume(KeywordToken('break')):
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
        function_name = self.id()
        self.__expect(SymbolToken('('))
        parameters = self.parameters()
        self.__expect(SymbolToken(')'))
        return_type = None
        if self.__accept_and_consume(SymbolToken(':')):
            return_type = self.type()
        self.__expect(SymbolToken('='))
        body = self.expression()
        return FunctionDeclaration(function_name, parameters, return_type, body)

    def id(self):
        token = self.__expect_type(IdentifierToken)
        return token.value

    def id_field(self):
        field_name = self.id()
        self.__expect(SymbolToken('='))
        exp = self.expression()
        return field_name, exp

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
        lvalue_name = self.id()
        next_lvalue = self.lvalue_next()
        return LValue(lvalue_name, next_lvalue)

    def lvalue_next(self):
        next_lvalue = None
        if self.__accept_and_consume(SymbolToken('.')):
            next_lvalue = self.record_lvalue()
        elif self.__accept_and_consume(SymbolToken('[')):
            next_lvalue = self.array_lvalue()
        return next_lvalue

    def lvalue_started(self, lvalue):
        if self.__accept_and_consume(SymbolToken(':=')):
            exp = self.expression()
            return Assign(lvalue, exp)
        elif self.__accept_and_consume(KeywordToken('of')):
            return self.array_from_lvalue(lvalue)
        else:
            return lvalue

    def operation(self, operation, left, right):
        operator_class = OPERATORS[operation]
        return operator_class(left, right)

    def parameters(self):
        if self.__accept_type(IdentifierToken):
            parameters = []
            name, type_id = self.type_field()
            parameters.append(FunctionParameter(name, type_id))
            while self.__accept_and_consume(SymbolToken(',')):
                name, type_id = self.type_field()
                parameters.append(FunctionParameter(name, type_id))
            return parameters
        else:
            return []

    def precedence(self, token):
        return PRECEDENCE[token.value]

    def record(self):
        type_token = self.__expect_type(IdentifierToken)
        self.__expect(SymbolToken('{'))
        fields = OrderedDict()
        while self.__accept_type(IdentifierToken):
            field_name, exp = self.id_field()
            fields[field_name] = exp
            token = self.__next()
            if self.__accept(SymbolToken(','), token):
                pass
            elif self.__accept(SymbolToken('}'), token):
                break
            else:
                raise ParseError('Expected either , or }', token)
            # TODO possibility for garbage after ', ...'
        return RecordCreation(TypeId(type_token.value), fields)

    def record_lvalue(self):
        lvalue_name = self.__expect_type(IdentifierToken)
        next_lvalue = self.lvalue_next()
        return RecordLValue(lvalue_name.value, next_lvalue)

    def sequence(self):
        exps = []
        self.__expect(SymbolToken('('))
        if not self.__peek().equals(SymbolToken(')')):
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
            type_fields = self.type_fields()
            self.__expect(SymbolToken('}'))
            return RecordType(type_fields)
        elif self.__accept(KeywordToken('array'), token):
            self.__expect(KeywordToken('of'))
            type_name = self.__expect_type(IdentifierToken)
            return ArrayType(type_name.value)
        else:
            raise ExpectationError('a type definition', token)

    def type_declaration(self):
        self.__expect(KeywordToken('type'))
        type_name = self.id()
        self.__expect(SymbolToken('='))
        ty = self.type()
        return TypeDeclaration(type_name, ty)

    def type_fields(self):
        type_fields = OrderedDict()
        if self.__accept_type(IdentifierToken):
            name, type_id = self.type_field()
            type_fields[name] = type_id
            while self.__accept_and_consume(SymbolToken(',')):
                name, type_id = self.type_field()
                type_fields[name] = type_id
        return type_fields

    def type_field(self):
        field_name = self.id()
        self.__expect(SymbolToken(':'))
        type_id = self.type_id()
        return field_name, type_id

    def type_id(self):
        type_id = self.__expect_type(IdentifierToken)
        return TypeId(type_id.value)

    def variable_declaration(self):
        self.__expect(KeywordToken('var'))
        name = self.id()
        type_id = None
        if self.__accept_and_consume(SymbolToken(':')):
            type_id = self.type()
        self.__expect(SymbolToken(':='))
        exp = self.expression()
        return VariableDeclaration(name, type_id, exp)

    def while_do(self):
        self.__expect(KeywordToken('while'))
        condition = self.expression()
        self.__expect(KeywordToken('do'))
        body = self.expression()
        return While(condition, body)

    # navigation methods

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
