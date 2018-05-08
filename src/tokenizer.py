from src.tokens import NumberToken, IdentifierToken, KeywordToken, SymbolToken, StringToken


class Location:
    def __init__(self, offset, line, file):
        self.offset = offset
        self.line = line
        self.file = file

    def __repr__(self):
        return "%s:%s" % (self.file if self.file else "<code string>", self.line)


class TokenError(Exception):
    def __init__(self, reason, location):
        self.reason = reason
        self.location = location


class Tokenizer:
    # TODO make some of these immutable

    def __init__(self, text, file=None):
        self.file = file
        self.text = text
        self.length = len(text)
        self.offset = 0
        self.line_offset = 0
        self.line = 1
        self.buffer = []

    def all(self):
        """Return all of the tokens in the text"""
        ts = []
        t = self.tokenize()
        while t:
            ts.append(t)
            t = self.tokenize()
        return ts

    def peek(self, index=0):
        """Peek at the next token (or optionally some number of tokens in) without consuming it"""
        while len(self.buffer) <= index:
            self.buffer.append(self.tokenize())
        return self.buffer[index]

    def next(self):
        if len(self.buffer):
            return self.buffer.pop(0)
        else:
            return self.tokenize()

    def tokenize(self):
        """Retrieve the next token from the text"""
        c = self.__current_character()
        while c:
            if self.is_whitespace(c):
                pass
            elif self.is_eol(c):
                self.__newline()  # do line accounting
            elif self.is_slash(c):
                self.__comment()  # advance until end of comment
            elif self.is_quote(c):
                location = self.current_location()
                return StringToken(self.__string(), location)
            elif self.is_number(c):
                location = self.current_location()
                return NumberToken(self.__number(), location)
            elif self.is_underscore(c):
                pass  # read _main
            elif self.is_letter(c):
                location = self.current_location()
                value = self.__identifier()
                if self.is_keyword(value):
                    return KeywordToken(value, location)
                else:
                    return IdentifierToken(value, location)
            elif self.is_symbol(c):
                location = self.current_location()
                d = self.__advance()
                if c == '<' and d in '>=':
                    return SymbolToken(c + d, location)
                elif c in '>:' and d == '=':
                    self.__advance()
                    return SymbolToken(c + d, location)
                else:
                    return SymbolToken(c, location)
            else:
                raise TokenError('Invalid character: ' + c, self.current_location())
            c = self.__advance()
        return None

    def current_location(self):
        """Retrieve a location reference for the current offset"""
        return Location(self.line_offset, self.line, self.file)

    # TODO inline
    @staticmethod
    def is_whitespace(c):
        return c == ' ' or c == '\t'

    @staticmethod
    def is_eol(c):
        return c == '\n' or c == '\r'

    @staticmethod
    def is_slash(c):
        return c == '/'

    @staticmethod
    def is_quote(c):
        return c == '"'

    @staticmethod
    def is_number(c):
        if not c:
            return False
        c_ = ord(c[0])  # note: there should only be one character here but RPython wants us to make this explicit
        return 48 <= c_ <= 57

    @staticmethod
    def is_letter(c):
        if not c:
            return False
        c_ = ord(c[0])  # note: there should only be one character here but RPython wants us to make this explicit
        return (65 <= c_ <= 90) or (97 <= c_ <= 122)  # uppercase ASCII, lowercase ASCII

    @staticmethod
    def is_underscore(c):
        return c == '_'

    @staticmethod
    def is_symbol(c):
        return c in ',:;()[]{}.+-*/=<>&|'

    @staticmethod
    def is_keyword(s):
        return s in ['array', 'if', 'then', 'else', 'while', 'for', 'to', 'do', 'let', 'in', 'end', 'of', 'break',
                     'nil', 'function', 'var', 'type', 'import', 'primitive',
                     'class', 'extends', 'method', 'new'  # object-related extension
                     ]

    def __comment(self):
        """Advance until end of comments (including nesting)"""
        c = self.__advance()
        if c != '*':
            raise TokenError('Expected comment; / without *', self.current_location())
        else:
            comment_level = 1
            while comment_level:
                self.__advance_until('/')
                if self.__previous_character() == '*':
                    comment_level -= 1
                elif self.__next_character() == '*':
                    comment_level += 1

    def __string(self):
        s = []  # TODO benchmark list append vs string concat (e.g. +=)
        c = self.__current_character()
        while c:
            c = self.__advance()
            if c == '\\':
                d = self.__advance()
                if d == '"':
                    s.append('"')
                elif d == '\\':
                    s.append('\\')
                elif d == 'x':
                    # hex number
                    n = int(self.__number(), 16)
                    s.append(str(n))
                elif self.is_number(d):
                    # octal number
                    n = int(self.__number(), 8)
                    s.append(str(n))
                # control characters (https://en.wikipedia.org/wiki/Escape_sequences_in_C)
                elif d == 'a':
                    raise TokenError('Not sure how to tokenize beeps', self.current_location())
                elif d == 'b':
                    s.pop()  # backspace
                elif d == 'f':
                    raise TokenError('Not sure how to tokenize a formfeed', self.current_location())
                elif d == 'n':
                    s.append('\n')
                elif d == 'r':
                    s.append('\r')
                elif d == 't':
                    s.append('\t')
                elif d == 'v':
                    raise TokenError('Not sure how to tokenize a vertical tab', self.current_location())
                else:
                    TokenError('Invalid escaped character within string: ' + d, self.current_location())
            elif c == '"':
                self.__advance()
                break
            else:
                s.append(c)
        return ''.join(s)

    def __number(self):
        n = [self.__current_character()]
        c = self.__advance()
        while self.is_number(c):
            n.append(c)
            c = self.__advance()
        return ''.join(n)

    def __identifier(self):
        i = [self.__current_character()]
        c = self.__advance()
        while self.is_letter(c) or self.is_number(c):
            i.append(c)
            c = self.__advance()
        return ''.join(i)

    def __previous_character(self):
        """Retrieve the character before the current offset as long as this is within the text"""
        if self.offset > 0:
            return self.text[self.offset - 1]
        else:
            return None

    # TODO inline?
    def __current_character(self):
        """Retrieve the character at the current offset"""
        if self.offset < self.length:
            return self.text[self.offset]
        else:
            return None

    def __next_character(self):
        """Retrieve the character after the current offset as long as this is within the text"""
        offset_ = self.offset + 1
        if offset_ < self.length:
            return self.text[offset_]
        else:
            return None

    def __newline(self):
        """Advance the cursor and return the character at this new location"""
        self.line += 1
        self.line_offset = 0

    def __advance(self):
        """Advance the cursor and return the character at this new location"""
        self.offset += 1
        self.line_offset += 1
        if self.offset < self.length:
            return self.text[self.offset]
        else:
            return None

    def __advance_until(self, match):
        """Advance the cursor until a match is found and return the character at this new location"""
        c = self.__advance()
        while c and c != match:
            c = self.__advance()
        return c

        # def __advance_until(self, match):
        #     c = self.__read()
        #     while c != '' and c:
        #         value += c
        #         c = self.__read()
        #     if c != '': self.__unread()
        #     return value
