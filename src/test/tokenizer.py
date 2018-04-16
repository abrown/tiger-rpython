import unittest

from src.tokenizer import *
from src.tokens import NumberToken, IdentifierToken, SymbolToken, StringToken


class TestTokenizer(unittest.TestCase):
    def assertTokenizesTo(self, text, expected_tokens):
        sut = Tokenizer(text)
        actual_tokens = sut.all()
        self.assertTokensEqual(expected_tokens, actual_tokens)

    def assertTokensEqual(self, expected, actual):
        if len(expected) is not len(actual):
            raise AssertionError("Lengths do not match: {} != {}".format(expected, actual))
        for i, e in enumerate(expected):
            self.assertIsInstance(actual[i], e.__class__)
            self.assertEqual(e.location, actual[i].location) if e.location else None
            self.assertEqual(e.value, actual[i].value) if e.value else None

    def test_simple(self):
        self.assertTokenizesTo("2 + 2", [NumberToken('2'), SymbolToken('+'), NumberToken('2')])

    def test_multiline(self):
        self.assertTokenizesTo("a = 1\nb = 2", [IdentifierToken('a'), SymbolToken('='), NumberToken('1'),
                                                IdentifierToken('b'), SymbolToken('='), NumberToken('2')])

    def test_string(self):
        self.assertTokenizesTo(' "a \\" \t" ', [StringToken('a " \t')])

    def test_assign(self):
        self.assertTokenizesTo('a := b', [IdentifierToken('a'), SymbolToken(':='), IdentifierToken('b')])


if __name__ == '__main__':
    unittest.main()
