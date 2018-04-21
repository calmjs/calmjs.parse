# -*- coding: utf-8 -*-
"""
ES2015 (ECMAScript 6th Edition/ES6) lexer.
"""

import ply

from calmjs.parse.lexers.es5 import Lexer as ES5Lexer


class Lexer(ES5Lexer):
    """
    ES2015 lexer.
    """

    # Punctuators (ES6)
    t_ARROW        = r'=>'
    t_SPREAD       = r'\.\.\.'
    # this is now a right brace operator...
    # t_RBRACE        = r'}'

    # TODO verify that the standard string rule will work.
    # TODO complete the actual implementation to make this actually
    # usable.
    template = r"""
    (?:`                               # opening backquote
        (?: [^`\\]                     # not `, \; allow
            | \\(\n|\r(?!\n)|\u2028|\u2029|\r\n)  # line continuation
            | \\[a-tvwyzA-TVWYZ!-\/:-@\[-`{-~] # escaped chars
            | \\x[0-9a-fA-F]{2}        # hex_escape_sequence
            | \\u[0-9a-fA-F]{4}        # unicode_escape_sequence
            | \\(?:[1-7][0-7]{0,2}|[0-7]{2,3}) # octal_escape_sequence
            | \\0                      # <NUL> (ECMA-262 6.0 21.2.2.11)
        )*?                            # zero or many times
    `)                                 # closing backquote
    """

    tokens = ES5Lexer.tokens + (
        # ES2015 punctuators
        'ARROW', 'SPREAD',    # => ...

        # ES2015 terminal types
        'TEMPLATE',
    )

    @ply.lex.TOKEN(template)
    def t_TEMPLATE(self, token):
        # remove escape + new line sequence used for strings
        # written across multiple lines of code
        token.value = token.value.replace('\\\n', '')
        return token
