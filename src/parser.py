from src.ast import Program, NilValue, IntegerValue, StringValue, ArrayCreation, TypeId
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
        self.accepted = []

    def parse(self):
        return self.expression()

    def expression(self):
        token = self.next()
        if self.accept(token, KeywordToken('nil')):
            return NilValue()
        elif self.accept_type(token, NumberToken):
            return IntegerValue(token.value)
        elif self.accept_type(token, StringToken):
            return StringValue(token.value)
        elif self.accept_type(token, IdentifierToken):
            return self.id_started()
        else:
            raise ParseError('Unable to parse', self.next())

    def id_started(self):
        token = self.next()
        if self.accept(token, SymbolToken('[')):
            return self.array()
        elif self.accept(token, SymbolToken('{')):
            return self.record()
        elif self.accept(token, SymbolToken('(')):
            return self.function_call()
        else:
            raise ParseError('Unable to parse', self.next())

    def array(self):
        type = self.next_or_accepted()
        self.expect(self.next_or_accepted(), SymbolToken('['))
        exp1 = self.expression()
        self.expect(self.next(), SymbolToken(']'))
        self.expect(self.next(), KeywordToken('of'))
        exp2 = self.expression()
        return ArrayCreation(TypeId(type.value), exp1, exp2)

    # navigation methods TODO make private

    def next(self):
        """Return the next token"""
        return self.tokenizer.next()

    def next_or_accepted(self):
        if len(self.accepted):
            return self.accepted.pop(0)
        else:
            return self.next()

    def accept(self, token, expected):
        if expected == token:
            self.accepted.append(token)
            return True
        else:
            return False

    def accept_type(self, token, type):
        if isinstance(token, type):
            self.accepted.append(token)
            return True
        else:
            return False

    def expect(self, token, expected):
        if self.accept(token, expected):
            return token
        else:
            raise ExpectationError(expected, token)


        #
        # def all(self):
        #     """Parse all tokens into a Module and return it"""
        #     while True:
        #         last = self.next()
        #         if last is None:
        #             break
        #     return self.module
        #
        # def __collect(self, token_type):
        #     tokens = []
        #     while True:
        #         token = self.tokenizer.next()
        #         if not isinstance(token, token_type):
        #             self.tokenizer.undo(token)
        #             break
        #         tokens.append(token)
        #     return tokens
        #
        # def __expect(self, token_type):
        #     token = self.tokenizer.next()
        #     if not isinstance(token, token_type):
        #         raise ParseError("Expected a token of %s but found something else" % token_type, token)
        #     return token
        #
        # def __expect_value(self, token_type, expected=None):
        #     token = self.__expect(token_type)
        #     if expected and token.value != expected:
        #         raise ParseError("Expected a token with value %s but found something else" % str(expected), token)
        #
        # def __possible(self, token_type):
        #     token = self.tokenizer.next()
        #     if isinstance(token, token_type):
        #         return token
        #     else:
        #         self.tokenizer.undo(token)
        #         return None
        #
        # def __possible_value(self, token_type, expected):
        #     token = self.tokenizer.next()
        #     if isinstance(token, token_type) and expected and token.value == expected:
        #         return token
        #     else:
        #         self.tokenizer.undo(token)
        #         return None
        #
        # def __parse_term(self):
        #     token = self.tokenizer.next()
        #     if isinstance(token, IdToken):
        #         return self.__parse_identifier(token)
        #     elif isinstance(token, NumberToken):
        #         return IntTerm(0 if token.value is None else int(token.value))
        #     elif isinstance(token, LeftBraceToken):
        #         return self.__parse_new_environment(token)
        #     elif isinstance(token, LeftBracketToken):
        #         return self.__parse_list(token)
        #     else:
        #         self.tokenizer.undo(token)
        #         return None
        #
        # def __parse_identifier(self, id_token):
        #     if self.__possible(LeftParensToken):
        #         args = []
        #         while True:
        #             arg = self.__parse_term()
        #             if arg is None:
        #                 break
        #             args.append(arg)
        #             self.__possible(CommaToken)
        #         self.__expect(RightParensToken)
        #         return ApplTerm(id_token.value, args)
        #     if self.__possible(LeftBracketToken):
        #         name = self.__expect(IdToken)
        #         self.__expect(RightBracketToken)
        #         return MapReadTerm(VarTerm(id_token.value), VarTerm(name.value))
        #     else:
        #         return VarTerm(id_token.value)
        #
        # def __parse_new_environment(self, token):
        #     assignments = {}
        #     while True:
        #         name = self.__parse_term()
        #         if name is None:
        #             break
        #         if not isinstance(name, VarTerm):
        #             raise ParseError("Expected a variable term but found " + str(name), None)
        #         if self.__possible_value(OperatorToken, "|-->"):
        #             value = self.__expect_term()
        #         else:
        #             value = MapWriteTerm()  # TODO this is by "convention" but not necessarily clear
        #         assignments[name] = value
        #         self.__possible(CommaToken)
        #     self.__expect(RightBraceToken)
        #     return MapWriteTerm(assignments)
        #
        # def __parse_list(self, token):
        #     items = []
        #
        #     # normal list
        #     while True:
        #         term = self.__parse_term()
        #         if term is None:
        #             break
        #         items.append(term)
        #         if not self.__possible(CommaToken):
        #             break
        #
        #     # list pattern
        #     if self.__possible_value(OperatorToken, "|"):
        #         for i in items:
        #             if not isinstance(i, VarTerm):
        #                 raise ParseError("Expected list pattern to only include VarTerms", token)
        #         rest = self.__expect_term()
        #         if not isinstance(rest, VarTerm):
        #             raise ParseError("Expected list pattern to only include VarTerms", token)
        #         self.__expect(RightBracketToken)
        #         return ListPatternTerm(items, rest)
        #     else:
        #         self.__expect(RightBracketToken)
        #         return ListTerm(items)
        #
        # def __expect_term(self):
        #     term = self.__parse_term()
        #     if term is None:
        #         raise ParseError("Expected to parse a term", self.tokenizer.next())
        #     return term
        #
        # def __parse_premise(self):
        #     if self.__possible_value(KeywordToken, "case"):
        #         return self.__parse_case()
        #
        #     left = self.__parse_term()
        #     operator = self.__expect(OperatorToken)
        #     right = self.__parse_term()
        #
        #     if "==" == operator.value:
        #         return EqualityCheckPremise(left, right)
        #     elif "=>" == operator.value:
        #         if isinstance(right, ApplTerm):
        #             return PatternMatchPremise(left, right)
        #         else:
        #             return AssignmentPremise(left, right)
        #     elif "-->" == operator.value:
        #         return ReductionPremise(left, right)
        #     else:
        #         raise NotImplementedError()
        #
        # def __parse_case(self):
        #     var = self.__expect_term()
        #     self.__expect_value(KeywordToken, "of")
        #     self.__expect(LeftBraceToken)
        #
        #     values = []
        #     sub_premises = []
        #     while True:
        #         if self.__possible_value(KeywordToken, "otherwise"):
        #             values.append(None)
        #         else:
        #             values.append(self.__expect_term())
        #         self.__expect_value(OperatorToken, "=>")
        #         sub_premises.append(self.__parse_premise())
        #         if self.__possible(RightBraceToken):
        #             break
        #
        #     return CasePremise(var, values, sub_premises)
        #
        # def __parse_rule(self):
        #     before = self.__expect_term()
        #
        #     # parse semantic components
        #     components = []
        #     if self.__possible_value(OperatorToken, "|-"):
        #         components.append(before)
        #         before = self.__expect_term()
        #
        #     # read body
        #     self.__expect_value(OperatorToken, "-->")
        #     after = self.__expect_term()
        #
        #     # parse premises
        #     premises = []
        #     if self.__possible_value(KeywordToken, "where"):
        #         while True:
        #             premise = self.__parse_premise()
        #             premises.append(premise)
        #             if not self.__possible(SemiColonToken):
        #                 break
        #         self.__possible(PeriodToken)
        #
        #     # assign slot numbers
        #     number_of_bound_terms = SlotAssigner().assign_rule(before, after, premises)
        #
        #     return Rule(before, after, components, premises, number_of_bound_terms)
