# -*- coding: utf-8 -*-
"""
ES2015 (ECMAScript 6th Edition/ES6) lexer.
"""

from __future__ import unicode_literals

import re
import ply
from itertools import chain

from calmjs.parse.utils import repr_compat
from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.lexers.es5 import Lexer as ES5Lexer

template_token_types = (
    (re.compile(r'`.*`', re.S),
        'TEMPLATE_NOSUB'),
    (re.compile(r'`.*\${', re.S),
        'TEMPLATE_HEAD'),
    (re.compile(r'}.*\${', re.S),
        'TEMPLATE_MIDDLE'),
    (re.compile(r'}.*`', re.S),
        'TEMPLATE_TAIL'),
)


es2015_keywords = (
    'LET',
    'STATIC',
    'YIELD',
)

PATT_BROKEN_TEMPLATE = re.compile(r"""
(?:(?:`|})                         # opening ` or }
    (?: [^`\\]                     # not `, \; allow
        | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
        | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
        | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
        | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
        | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3}) # octal_escape_sequence
        | \\0                      # <NUL> (ECMA-262 6.0 21.2.2.11)
    )*                             # zero or many times
)                                  # omit closing ` or ${
""", flags=re.VERBOSE)


def broken_template_token_handler(lexer, token):
    match = PATT_BROKEN_TEMPLATE.match(token.value)
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

    if lexer.current_template_tokens:
        # join all tokens together
        tmpl = '...'.join(
            t.value for t in chain(lexer.current_template_tokens[-1], [token]))
        lineno = lexer.current_template_tokens[-1][0].lineno
        colno = lexer.current_template_tokens[-1][0].colno
    else:
        tmpl = token.value
        lineno = token.lineno

    raise ECMASyntaxError('Unterminated template literal %s at %s:%s' % (
        repr_compat(tmpl[:tl].strip() + (tmpl[tl:] and '...')), lineno, colno))


class Lexer(ES5Lexer):
    """
    ES2015 lexer.
    """

    def __init__(self, with_comments=False, yield_comments=False):
        super(Lexer, self).__init__(
            with_comments=with_comments, yield_comments=yield_comments)
        self.error_token_handlers.append(broken_template_token_handler)
        self.current_template_tokens = []
        self.current_template_tokens_braces = []

    # Punctuators (ES6)
    # t_DOLLAR_LBRACE  = r'${'
    # this is also a right brace punctuator...
    # t_RBRACE        = r'}'
    t_ARROW          = r'=>'
    t_SPREAD         = r'\.\.\.'

    keywords = ES5Lexer.keywords + es2015_keywords
    keywords_dict = dict((key.lower(), key) for key in keywords)

    tokens = ES5Lexer.tokens + es2015_keywords + (
        # ES2015 punctuators
        'ARROW', 'SPREAD',    # => ...

        # ES2015 terminal types
        'TEMPLATE_NOSUB', 'TEMPLATE_HEAD', 'TEMPLATE_MIDDLE', 'TEMPLATE_TAIL',
    )

    t_NUMBER = r"""
    (?: 0[bB][01]+                     # binary_integer_literal
     |  0[oO][0-7]+                    # or octal_integer_literal
     |  0[xX][0-9a-fA-F]+              # or hex_integer_literal
     |  0[0-7]+                        # or legacy_octal_integer_literal
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

    template = r"""
    (?:(?:`|})                         # opening ` or }
        (?: [^`\\]                     # not `, \; allow
            | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
            | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
            | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
            | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
            | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3}) # octal_escape_sequence
            | \\0                      # <NUL> (ECMA-262 6.0 21.2.2.11)
        )*?                            # zero or many times
    (?:`|\${))                         # closing ` or ${
    """

    LBRACE        = r'{'
    RBRACE        = r'}'

    @ply.lex.TOKEN(template)
    def t_TEMPLATE_RAW(self, token):
        for patt, token_type in template_token_types:
            if patt.match(token.value):
                token.type = token_type
                break
        else:
            raise ValueError("invalid token %r" % token)

        if token.type == 'TEMPLATE_HEAD':
            self.current_template_tokens.append([token])
            self.current_template_tokens_braces.append(0)
            return token
        elif token.type == 'TEMPLATE_NOSUB':
            return token

        if not self.current_template_tokens_braces:
            raise ECMASyntaxError('Unexpected %s at %s:%s' % (
                repr_compat('}'), token.lineno, self._get_colno(token)))
        if self.current_template_tokens_braces[-1] > 0:
            # produce a LBRACE token instead
            self.current_template_tokens_braces[-1] -= 1
            self.lexer.lexpos = self.lexer.lexpos - len(token.value) + 1
            token.value = token.value[0]
            token.type = 'RBRACE'
            return token

        if token.type == 'TEMPLATE_MIDDLE':
            self.current_template_tokens[-1].append(token)
        elif token.type == 'TEMPLATE_TAIL':
            self.current_template_tokens_braces.pop()
            self.current_template_tokens.pop()
        return token

    @ply.lex.TOKEN(LBRACE)
    def t_LBRACE(self, token):
        if self.current_template_tokens_braces:
            self.current_template_tokens_braces[-1] += 1
        return token

    @ply.lex.TOKEN(RBRACE)
    def t_RBRACE(self, token):
        if self.current_template_tokens:
            self.lexer.lexpos = self.lexer.lexpos - 1
            token.value = self.lexer.lexdata[self.lexer.lexpos:]
            broken_template_token_handler(self, token)
        return token
