from src.ast import NilValue, IntegerValue, StringValue, ArrayCreation, TypeId, RecordCreation, LValue, \
    ObjectCreation, FunctionCall, RecordLValue, ArrayLValue, Assign, MethodCall, If, While, For, Break, Let
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
            elif token.value == 'class':
                return self.class_declaration()
            elif token.value == 'var':
                return self.variable_declaration()
            elif token.value == 'function':
                return self.function_declaration()
            elif token.value == 'primitive':
                return self.primitive_declaration()
            elif token.value == 'import':
                return self.import_declaration()
            else:
                raise ExpectationError('Expected keyword in {type, class, var, function, primitive, import}', token)
        else:
            self.remember(token)
        return None

    def type_declaration(self):
        self.expect(self.next_or_remembered(), KeywordToken('type'))
        id = self.expect(self.next_or_remembered(), IdentifierToken)
        self.expect(self.next(), SymbolToken('='))
        ty = self.type()
        return TypeDeclaration(id.value, ty)

    def type(self):
        token = self.next_or_remembered()
        if self.accept(token, IdentifierToken):
            return TypeId(token.value)
        elif self.accept(token, SymbolToken('{')):
            return self.type_fields()
        elif self.accept(token, KeywordToken('array')):
            self.expect(self.next(), KeywordToken('of'))
            id = self.expect(self.next(), IdentifierToken)
            return ArrayType(id.value)
        elif self.accept_and_remember(token, KeywordToken('class')):
            return self.class_definition()
        else:
            raise ExpectationError('Expected a type definition', token)

    def class_definition(self):
        self.expect(self.next_or_remembered(), KeywordToken('class'))
        id = self.expect(self.next_or_remembered(), IdentifierToken)
        extends = None
        token = self.next()
        if self.accept(token, KeywordToken('extends')):
            extends = self.expect(self.next(), IdentifierToken)
            token = self.next()
        self.expect(token, SymbolToken('{'))
        variables, methods = self.class_fields()
        self.expect(token, SymbolToken('}'))
        return ClassDefinition(id.value, extends.value if extends else None, variables, methods)

    def class_fields(self):
        variables = {}
        methods = {}
        token = self.next_or_remembered()
        if self.accept_and_remember(token, KeywordToken('var')):
            variable = self.variable_declaration()
            variables[variable.name] = variable
        elif self.accept_and_remember(token, KeywordToken('method')):
            method = self.method()
            methods[method.name] = method
        else:
            self.remember(token)
        return variables, methods

    def variable_declaration(self):
        self.expect(self.next_or_remembered(), KeywordToken('var'))
        id = self.expect_id(self.next_or_remembered())
        token = self.next_or_remembered()
        type_id = None
        if self.accept(token, SymbolToken(':')):
            type_id = self.expect_id(self.next())
            token = self.next()
        self.expect(self.next(), KeywordToken(':='))
        exp = self.expression()
        return VariableDeclaration(id.value, type_id.value if type_id else None, exp)

    def method_declaration(self):
        self.expect(self.next_or_remembered(), KeywordToken('method'))
        id = self.expect_id(self.next_or_remembered())
        self.expect(self.next(), SymbolToken('('))
        type_fields = self.type_fields()
        self.expect(self.next(), SymbolToken(')'))
        return_type = None
        token = self.next()
        if self.accept(token, SymbolToken(':')):
            return_type = self.type_id()
            token = self.next()
        self.expect(token, SymbolToken('='))
        exp = self.expression()
        return MethodDeclaration(id, type_fields, return_type, exp)

    def type_fields(self):
        token = self.next_or_remembered()
        if self.accept(token, IdentifierToken):
            type_fields = {}
            name, type_id = self.type_field()
            type_fields[name] = type_id
            while
        else:
            self.remember(token)
            return {}
        token = self.expect_id(self.next_or_remembered())


    def type_id(self):
        return self.expect(self.next_or_remembered(), IdentifierToken).value

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
