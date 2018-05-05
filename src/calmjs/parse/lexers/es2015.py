# -*- coding: utf-8 -*-
"""
ES2015 (ECMAScript 6th Edition/ES6) lexer.
"""

import re
import ply

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
)


class Lexer(ES5Lexer):
    """
    ES2015 lexer.
    """

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

    @ply.lex.TOKEN(template)
    def t_TEMPLATE_RAW(self, token):
        for patt, token_type in template_token_types:
            if patt.match(token.value):
                token.type = token_type
        return token
