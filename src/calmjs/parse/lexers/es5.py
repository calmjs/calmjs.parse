###############################################################################
#
# Copyright (c) 2011 Ruslan Spivak
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from __future__ import unicode_literals

__author__ = 'Ruslan Spivak <ruslan.spivak@gmail.com>'

import re
import ply.lex

from calmjs.parse.lexers.tokens import AutoLexToken
from calmjs.parse.utils import repr_compat
from calmjs.parse.exceptions import (
    ECMASyntaxError,
    ECMARegexSyntaxError,
)
from calmjs.parse.unicode_chars import (
    LETTER,
    DIGIT,
    COMBINING_MARK,
    CONNECTOR_PUNCTUATION,
)
from calmjs.parse.utils import format_lex_token

# See "Regular Expression Literals" at
# http://www.mozilla.org/js/language/js20-2002-04/rationale/syntax.html
TOKENS_THAT_IMPLY_DIVISON = frozenset([
    'ID',
    'NUMBER',
    'STRING',
    'REGEX',
    'TRUE',
    'FALSE',
    'NULL',
    'THIS',
    'PLUSPLUS',
    'MINUSMINUS',
    'RPAREN',
    'RBRACE',
    'RBRACKET',
])

IMPLIED_BLOCK_IDENTIFIER = frozenset([
    'FOR',
    'WHILE',
    'IF',
])


# think of a better name for this, but this is mostly to address section
# 7 of the spec.
DIVISION_SYNTAX_MARKERS = frozenset([
    'LINE_TERMINATOR', 'LINE_COMMENT', 'BLOCK_COMMENT'
])

COMMENTS = frozenset([
    'LINE_COMMENT', 'BLOCK_COMMENT'
])

PATT_LINE_TERMINATOR_SEQUENCE = re.compile(
    r'(\n|\r(?!\n)|\u2028|\u2029|\r\n)', flags=re.S)
PATT_LINE_CONTINUATION = re.compile(
    r'\\(\n|\r(?!\n)|\u2028|\u2029|\r\n)', flags=re.S)


PATT_BROKEN_STRING = re.compile(r"""
(?:
    # broken double quoted string
    (?:"                               # opening double quote
        (?: [^"\\\n\r\u2028\u2029]     # not ", \, line terminators; allow
            | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
            | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
            | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
            | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
            | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3})  # octal_escape_sequence
            | \\0                      # <NUL> (15.10.2.11)
        )*                             # and capture them greedily
    )                                  # omit closing quote
    |
    # broken single quoted string
    (?:'                               # opening single quote
        (?: [^'\\\n\r\u2028\u2029]     # not ', \, line terminators; allow
            | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
            | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
            | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
            | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
            | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3}) # octal_escape_sequence
            | \\0                      # <NUL> (15.10.2.11)
        )*                             # and capture them greedily
    )                                  # omit closing quote
)
""", flags=re.VERBOSE)


def broken_string_token_handler(lexer, token):
    match = PATT_BROKEN_STRING.match(token.value)
    if not match:
        return

    # update the error token value to only include what was matched here
    # as this will be the actual token that "failed"
    token.value = match.group()
    # calculate colno for current token colno before...
    colno = lexer._get_colno(token)
    # updating the newline indexes for the error reporting for raw
    # lexpos
    lexer._update_newline_idx(token)
    # probe for the next values (which no valid rules will match)
    position = lexer.lexer.lexpos + len(token.value)
    failure = lexer.lexer.lexdata[position:position + 2]
    if failure and failure[0] == '\\':
        type_ = {'x': 'hexadecimal', 'u': 'unicode'}[failure[1]]
        seq = re.match(
            r'\\[xu][0-9-a-f-A-F]*', lexer.lexer.lexdata[position:]
        ).group()
        raise ECMASyntaxError(
            "Invalid %s escape sequence '%s' at %s:%s" % (
                type_, seq, lexer.lineno,
                lexer._get_colno_lexpos(position)
            )
        )
    tl = 16  # truncate length
    raise ECMASyntaxError(
        'Unterminated string literal %s at %s:%s' % (
            repr_compat(
                token.value[:tl].strip() + (token.value[tl:] and '...')),
            token.lineno, colno)
    )


class Lexer(object):
    """A JavaScript lexer.

    >>> from calmjs.parse.lexers.es5 import Lexer
    >>> lexer = Lexer()

    Lexer supports iteration:

    >>> lexer.input('a = 1;')
    >>> for token in lexer:
    ...     print(str(token).replace("u'", "'"))
    ...
    LexToken(ID,'a',1,0)
    LexToken(EQ,'=',1,2)
    LexToken(NUMBER,'1',1,4)
    LexToken(SEMI,';',1,5)

    Or call one token at a time with 'token' method:

    >>> lexer.input('a = 1;')
    >>> while True:
    ...     token = lexer.token()
    ...     if not token:
    ...         break
    ...     print(str(token).replace("u'", "'"))
    ...
    LexToken(ID,'a',1,0)
    LexToken(EQ,'=',1,2)
    LexToken(NUMBER,'1',1,4)
    LexToken(SEMI,';',1,5)

    >>> lexer.input('a = 1;')
    >>> token = lexer.token()
    >>> str(token.type), str(token.value), token.lineno, token.lexpos
    ('ID', 'a', 1, 0)

    For more information see:
    http://www.ecma-international.org/publications/files/ECMA-ST/ECMA-262.pdf
    """
    def __init__(self, with_comments=False, yield_comments=False):
        self.lexer = None
        self.prev_token = None
        # valid_prev_token is for syntax error hint, and also for
        # tracking real tokens
        self.valid_prev_token = None
        self.cur_token = None
        self.cur_token_real = None
        self.next_tokens = []
        self.token_stack = [[None, []]]
        self.newline_idx = [0]
        self.error_token_handlers = [
            broken_string_token_handler,
        ]
        self.with_comments = with_comments
        self.yield_comments = yield_comments
        self.hidden_tokens = []
        self.build()

        if not with_comments:
            # just reassign the method.
            self.token = self._token

    @property
    def lineno(self):
        return self.lexer.lineno if self.lexer else 0

    @property
    def lexpos(self):
        return self.lexer.lexpos if self.lexer else 0

    @property
    def last_newline_lexpos(self):
        return self.newline_idx[-1]

    def build(self, **kwargs):
        """Build the lexer."""
        self.lexer = ply.lex.lex(object=self, **kwargs)

    def input(self, text):
        self.lexer.input(text)

    def _update_newline_idx(self, token):
        lexpos = token.lexpos
        fragments = PATT_LINE_TERMINATOR_SEQUENCE.split(token.value)
        for fragment, newline in zip(*[iter(fragments)] * 2):
            lexpos += len(fragment + newline)
            self.lexer.lineno += 1
            self.newline_idx.append(lexpos)

    def get_lexer_token(self):
        token = self.lexer.token()
        if token:
            token.colno = self._get_colno(token)
            self._update_newline_idx(token)
        return token

    def backtracked_token(self, pos=1):
        self.lexer.skip(- pos)
        # clearly the buffer here needs wiping too
        self.next_tokens = []
        # do the dance to ensure the valid previous tokens are tracked.
        valid_prev_token = self.valid_prev_token
        token = self.token()
        self.valid_prev_token = valid_prev_token
        return token

    def token(self):
        token = self._token()
        if token and self.hidden_tokens:
            token.hidden_tokens = self.hidden_tokens
            self.hidden_tokens = []
        return token

    def _token(self):
        # auto-semi tokens that got added
        if self.next_tokens:
            return self.next_tokens.pop()

        lexer = self.lexer
        while True:
            pos = lexer.lexpos
            try:
                char = lexer.lexdata[pos]
                while char in ' \t':
                    pos += 1
                    char = lexer.lexdata[pos]
                next_char = lexer.lexdata[pos + 1]
            except IndexError:
                tok = self._get_update_token()
                if tok is not None and tok.type == 'LINE_TERMINATOR':
                    # should this also be implemented?
                    # if not self.drop_lineterm:
                    #     self.hidden_tokens.append(tok)
                    continue
                else:
                    return tok

            if char != '/' or (char == '/' and next_char in ('/', '*')):
                tok = self._get_update_token()
                if tok.type in DIVISION_SYNTAX_MARKERS:
                    if tok.type in COMMENTS:
                        if self.yield_comments:
                            return tok
                        elif self.with_comments:
                            self.hidden_tokens.append(tok)
                    continue
                else:
                    return tok

            # current character is '/' which is either division or regex
            # First check that if the previous token is a potential
            # division syntax marker that matches section 7.  If so, use
            # the previous token.
            check_token = (
                self.cur_token_real
                if self.cur_token_real is None or
                self.cur_token_real.type not in DIVISION_SYNTAX_MARKERS else
                self.prev_token
            )
            is_division_allowed = (
                check_token is not None and
                check_token.type in TOKENS_THAT_IMPLY_DIVISON
            ) and (
                self.token_stack[-1][0] is None or (
                    # if the token on the stack is the same, the
                    # following was done already, so skip it
                    self.token_stack[-1][0] is self.prev_token or
                    self.token_stack[-1][0].type in TOKENS_THAT_IMPLY_DIVISON
                )
            )
            if is_division_allowed:
                return self._get_update_token()
            else:
                self._set_tokens(self._read_regex())
                return self.cur_token

    def auto_semi(self, token):
        if token is None or (token.type not in ('SEMI', 'AUTOSEMI') and (
                token.type == 'RBRACE' or self._is_prev_token_lt())):
            if token:
                self.next_tokens.append(token)
            return self._create_semi_token(token)

    def _set_tokens(self, new_token):
        self.token_stack[-1][0] = self.prev_token = self.cur_token
        if (self.cur_token and
                self.cur_token.type not in DIVISION_SYNTAX_MARKERS):
            self.valid_prev_token = self.cur_token
        self.cur_token = new_token
        if (self.cur_token and
                self.cur_token.type not in DIVISION_SYNTAX_MARKERS):
            self.cur_token_real = self.cur_token

    def _is_prev_token_lt(self):
        return self.prev_token and self.prev_token.type == 'LINE_TERMINATOR'

    def _read_regex(self):
        self.lexer.begin('regex')
        token = self.get_lexer_token()
        self.lexer.begin('INITIAL')
        return token

    def _get_update_token(self):
        self._set_tokens(self.get_lexer_token())

        if self.cur_token is not None:

            if self.cur_token.type in ('LPAREN',):
                # if we encounter a FOR, IF, WHILE, then whatever in
                # the parentheses are marked.  Otherwise just push
                # into the inner marker list.
                if (self.prev_token and
                        self.prev_token.type in IMPLIED_BLOCK_IDENTIFIER):
                    self.token_stack.append([self.cur_token, []])
                else:
                    self.token_stack[-1][1].append(self.cur_token)

            if self.cur_token.type in ('RPAREN',):
                # likewise, pop the inner marker first.
                if self.token_stack[-1][1]:
                    self.token_stack[-1][1].pop()
                else:
                    self.token_stack.pop()

            if not self.token_stack:
                # TODO actually give up earlier than this with the first
                # mismatch.
                raise ECMASyntaxError(
                    "Mismatched '%s' at %d:%d" % (
                        self.cur_token.value,
                        self.cur_token.lineno,
                        self.cur_token.colno,
                    )
                )

        # insert semicolon before restricted tokens
        # See section 7.9.1 ECMA262
        if (self.cur_token is not None
            and self.cur_token.type == 'LINE_TERMINATOR'
            and self.prev_token is not None
            and self.prev_token.type in ['BREAK', 'CONTINUE',
                                         'RETURN', 'THROW']):
            return self._create_semi_token(self.cur_token)

        return self.cur_token

    def _get_colno(self, token):
        # have a 1 offset to map nicer to commonly used/configured
        # text editors.
        return self._get_colno_lexpos(token.lexpos)

    def _get_colno_lexpos(self, lexpos):
        return lexpos - self.last_newline_lexpos + 1

    def lookup_colno(self, lineno, lexpos):
        """
        Look up a colno from the lineno and lexpos.
        """

        # have a 1 offset to map nicer to commonly used/configured
        # text editors.
        return lexpos - self.newline_idx[lineno - 1] + 1

    def _create_semi_token(self, orig_token):
        token = AutoLexToken()
        token.type = 'AUTOSEMI'
        token.value = ';'
        if orig_token is not None:
            token.lineno = orig_token.lineno
            # TODO figure out whether/how to normalize this with the
            # actual length of the original token...
            # Though, if actual use case boils down to error reporting,
            # line number is sufficient, and leaving it as 0 means it
            # shouldn't get dealt with during source map generation.
            token.colno = 0
            token.lexpos = orig_token.lexpos
        else:
            token.lineno = 0
            token.lexpos = 0
            token.colno = 0
        return token

    # iterator protocol
    def __iter__(self):
        return self

    def next(self):
        token = self.token()
        if not token:
            raise StopIteration

        return token

    __next__ = next

    states = (
        ('regex', 'exclusive'),
    )

    keywords = (
        'BREAK', 'CASE', 'CATCH', 'CONTINUE', 'DEBUGGER', 'DEFAULT', 'DELETE',
        'DO', 'ELSE', 'FINALLY', 'FOR', 'FUNCTION', 'IF', 'IN',
        'INSTANCEOF', 'NEW', 'RETURN', 'SWITCH', 'THIS', 'THROW', 'TRY',
        'TYPEOF', 'VAR', 'VOID', 'WHILE', 'WITH', 'NULL', 'TRUE', 'FALSE',
        # future reserved words - well, it's uncommented now to make
        # IE8 happy because it chokes up on minification:
        # obj["class"] -> obj.class
        'CLASS', 'CONST', 'ENUM', 'EXPORT', 'EXTENDS', 'IMPORT', 'SUPER',
    )
    keywords_dict = dict((key.lower(), key) for key in keywords)

    tokens = (
        # Punctuators
        'PERIOD', 'COMMA', 'SEMI', 'COLON',     # . , ; :
        'AUTOSEMI',                             # autogenerated ;
        'PLUS', 'MINUS', 'MULT', 'DIV', 'MOD',  # + - * / %
        'BAND', 'BOR', 'BXOR', 'BNOT',          # & | ^ ~
        'CONDOP',                               # conditional operator ?
        'NOT',                                  # !
        'LPAREN', 'RPAREN',                     # ( and )
        'LBRACE', 'RBRACE',                     # { and }
        'LBRACKET', 'RBRACKET',                 # [ and ]
        'EQ', 'EQEQ', 'NE',                     # = == !=
        'STREQ', 'STRNEQ',                      # === and !==
        'LT', 'GT',                             # < and >
        'LE', 'GE',                             # <= and >=
        'OR', 'AND',                            # || and &&
        'PLUSPLUS', 'MINUSMINUS',               # ++ and --
        'LSHIFT',                               # <<
        'RSHIFT', 'URSHIFT',                    # >> and >>>
        'PLUSEQUAL', 'MINUSEQUAL',              # += and -=
        'MULTEQUAL', 'DIVEQUAL',                # *= and /=
        'LSHIFTEQUAL',                          # <<=
        'RSHIFTEQUAL', 'URSHIFTEQUAL',          # >>= and >>>=
        'ANDEQUAL', 'MODEQUAL',                 # &= and %=
        'XOREQUAL', 'OREQUAL',                  # ^= and |=

        # Terminal types
        'NUMBER', 'STRING', 'ID', 'REGEX',

        # Properties
        'GETPROP', 'SETPROP',

        # Comments
        'LINE_COMMENT', 'BLOCK_COMMENT',

        'LINE_TERMINATOR',
    ) + keywords

    # adapted from https://bitbucket.org/ned/jslex
    t_regex_REGEX = r"""(?:
        /                       # opening slash
        # First character is..
        (?: [^*\\/[]            # anything but * \ / or [
        |   \\.                 # or an escape sequence
        |   \[                  # or a class, which has
                (?: [^\]\\]     # anything but \ or ]
                |   \\.         # or an escape sequence
                )*              # many times
            \]
        )
        # Following characters are same, except for excluding a star
        (?: [^\\/[]             # anything but \ / or [
        |   \\.                 # or an escape sequence
        |   \[                  # or a class, which has
                (?: [^\]\\]     # anything but \ or ]
                |   \\.         # or an escape sequence
                )*              # many times
            \]
        )*                      # many times
        /                       # closing slash
        [a-zA-Z0-9]*            # trailing flags
        )
        """

    t_regex_ignore = ' \t'

    def t_regex_error(self, token):
        raise ECMARegexSyntaxError(
            "Error parsing regular expression '%s' at %s:%s" % (
                token.value, token.lineno, self._get_colno(token))
        )

    # Punctuators
    t_PERIOD        = r'\.'
    t_COMMA         = r','
    t_SEMI          = r';'
    t_COLON         = r':'
    t_PLUS          = r'\+'
    t_MINUS         = r'-'
    t_MULT          = r'\*'
    t_DIV           = r'/'
    t_MOD           = r'%'
    t_BAND          = r'&'
    t_BOR           = r'\|'
    t_BXOR          = r'\^'
    t_BNOT          = r'~'
    t_CONDOP        = r'\?'
    t_NOT           = r'!'
    t_LPAREN        = r'\('
    t_RPAREN        = r'\)'
    t_LBRACE        = r'{'
    t_RBRACE        = r'}'
    t_LBRACKET      = r'\['
    t_RBRACKET      = r'\]'
    t_EQ            = r'='
    t_EQEQ          = r'=='
    t_NE            = r'!='
    t_STREQ         = r'==='
    t_STRNEQ        = r'!=='
    t_LT            = r'<'
    t_GT            = r'>'
    t_LE            = r'<='
    t_GE            = r'>='
    t_OR            = r'\|\|'
    t_AND           = r'&&'
    t_PLUSPLUS      = r'\+\+'
    t_MINUSMINUS    = r'--'
    t_LSHIFT        = r'<<'
    t_RSHIFT        = r'>>'
    t_URSHIFT       = r'>>>'
    t_PLUSEQUAL     = r'\+='
    t_MINUSEQUAL    = r'-='
    t_MULTEQUAL     = r'\*='
    t_DIVEQUAL      = r'/='
    t_LSHIFTEQUAL   = r'<<='
    t_RSHIFTEQUAL   = r'>>='
    t_URSHIFTEQUAL  = r'>>>='
    t_ANDEQUAL      = r'&='
    t_MODEQUAL      = r'%='
    t_XOREQUAL      = r'\^='
    t_OREQUAL       = r'\|='

    t_LINE_COMMENT  = r'//[^\r\n\u2028\u2029]*'
    t_BLOCK_COMMENT = r'/\*[^*]*\*+([^/*][^*]*\*+)*/'

    # 7.3 Line Terminators
    t_LINE_TERMINATOR = r'(\n|\r(?!\n)|\u2028|\u2029|\r\n)'

    t_ignore = (
        # space, tab, line tab, form feed, nbsp
        u' \t\x0b\x0c\xa0'
        # ogham space mark
        u'\u1680'
        # en quad .. hair space
        u'\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A'
        # line sep, paragraph sep, narrow nbsp, med math, ideographic space
        u'\u2028\u2029\u202F\u205F\u3000'
        # unicode bom
        u'\uFEFF'
    )

    t_NUMBER = r"""
    (?:
        0[xX][0-9a-fA-F]+              # hex_integer_literal
     |  0[0-7]+                        # or octal_integer_literal
     |  (?:                            # or decimal_literal
            (?:0|[1-9][0-9]*)          # decimal_integer_literal
            \.                         # dot
            [0-9]*                     # decimal_digits_opt
            (?:[eE][+-]?[0-9]+)?       # exponent_part_opt
         |
            \.                         # dot
            [0-9]+                     # decimal_digits
            (?:[eE][+-]?[0-9]+)?       # exponent_part_opt
         |
            (?:0|[1-9][0-9]*)          # decimal_integer_literal
            (?:[eE][+-]?[0-9]+)?       # exponent_part_opt
         )
    )
    """

    string = r"""
    (?:
        # double quoted string
        (?:"                               # opening double quote
            (?: [^"\\\n\r\u2028\u2029]     # not ", \, line terminators; allow
                | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
                | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
                | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
                | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
                | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3})  # octal_escape_sequence
                | \\0                      # <NUL> (15.10.2.11)
            )*?                            # zero or many times
        ")                                 # must have closing double quote
        |
        # single quoted string
        (?:'                               # opening single quote
            (?: [^'\\\n\r\u2028\u2029]     # not ', \, line terminators; allow
                | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
                | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
                | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
                | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
                | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3}) # octal_escape_sequence
                | \\0                      # <NUL> (15.10.2.11)
            )*?                            # zero or many times
        ')                                 # must have closing single quote
    )
    """

    @ply.lex.TOKEN(string)
    def t_STRING(self, token):
        return token

    # XXX: <ZWNJ> <ZWJ> ?
    identifier_start = r'(?:' + r'[a-zA-Z_$]' + r'|' + LETTER + r')+'
    identifier_part = (
        r'(?:' + COMBINING_MARK + r'|' + r'[0-9a-zA-Z_$]' + r'|' + DIGIT +
        r'|' + CONNECTOR_PUNCTUATION + r')*'
    )
    identifier = identifier_start + identifier_part

    getprop = r'get' + r'(?=\s' + identifier + r')'

    @ply.lex.TOKEN(getprop)
    def t_GETPROP(self, token):
        return token

    setprop = r'set' + r'(?=\s' + identifier + r')'

    @ply.lex.TOKEN(setprop)
    def t_SETPROP(self, token):
        return token

    @ply.lex.TOKEN(identifier)
    def t_ID(self, token):
        token.type = self.keywords_dict.get(token.value, 'ID')
        return token

    def t_error(self, token):
        for handler in self.error_token_handlers:
            handler(self, token)

        if self.cur_token:
            # TODO make use of the extended calling signature when done
            raise ECMASyntaxError(
                'Illegal character %s at %s:%s after %s' % (
                    repr_compat(token.value[0]), token.lineno,
                    self._get_colno(token), format_lex_token(self.cur_token),
                )
            )
        else:
            raise ECMASyntaxError(
                'Illegal character %s at %s:%s' % (
                    repr_compat(token.value[0]), token.lineno,
                    self._get_colno(token),
                )
            )
