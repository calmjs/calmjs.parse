###############################################################################
# encoding: utf-8
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

__author__ = 'Ruslan Spivak <ruslan.spivak@gmail.com>'

import unittest

from calmjs.parse.lexers.es5 import Lexer
from calmjs.parse.exceptions import ECMASyntaxError

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase


class LexerFailureTestCase(unittest.TestCase):

    def test_illegal_unicode_char_in_identifier(self):
        lexer = Lexer()
        lexer.input(u'\u0036_tail')
        token = lexer.token()
        # \u0036_tail is the same as 6_tail and that's not a correct ID
        # Check that the token is NUMBER and not an ID
        self.assertEqual(token.type, 'NUMBER')
        self.assertEqual(token.value, '6')


def run_lex(value):
    lexer = Lexer()
    lexer.input(value)
    return ['%s %s' % (token.type, token.value) for token in lexer]


# The structure and some test cases are taken
# from https://bitbucket.org/ned/jslex
LexerTestCase = build_equality_testcase(
    'LexerTestCase', run_lex, ((
        label, data[0], data[1],
    ) for label, data in [(
        # Identifiers
        'identifiers_ascii',
        ('i my_variable_name c17 _dummy $str $ _ CamelCase class2type',
         ['ID i', 'ID my_variable_name', 'ID c17', 'ID _dummy',
          'ID $str', 'ID $', 'ID _', 'ID CamelCase', 'ID class2type']
         ),
    ), (
        'identifiers_unicode',
        (u'\u03c0 \u03c0_tail var\ua67c',
         [u'ID \u03c0', u'ID \u03c0_tail', u'ID var\ua67c']),
    ), (
        # https://github.com/rspivak/slimit/issues/2
        'slimit_issue_2',
        ('nullify truelie falsepositive',
         ['ID nullify', 'ID truelie', 'ID falsepositive']),

    ), (
        # Keywords
        # ('break case ...', ['BREAK break', 'CASE case', ...])
        'keywords_all',
        (' '.join(kw.lower() for kw in Lexer.keywords),
         ['%s %s' % (kw, kw.lower()) for kw in Lexer.keywords]
         ),
    ), (
        'keywords_break',
        ('break Break BREAK', ['BREAK break', 'ID Break', 'ID BREAK']),
    ), (
        # Literals
        'literals',
        ('null true false Null True False',
         ['NULL null', 'TRUE true', 'FALSE false',
          'ID Null', 'ID True', 'ID False']
         ),
    ), (
        # Punctuators
        'punctuators_simple',
        ('a /= b', ['ID a', 'DIVEQUAL /=', 'ID b']),
    ), (
        'punctuators_various_equality',
        (('= == != === !== < > <= >= || && ++ -- << >> '
          '>>> += -= *= <<= >>= >>>= &= %= ^= |='),
         ['EQ =', 'EQEQ ==', 'NE !=', 'STREQ ===', 'STRNEQ !==', 'LT <',
          'GT >', 'LE <=', 'GE >=', 'OR ||', 'AND &&', 'PLUSPLUS ++',
          'MINUSMINUS --', 'LSHIFT <<', 'RSHIFT >>', 'URSHIFT >>>',
          'PLUSEQUAL +=', 'MINUSEQUAL -=', 'MULTEQUAL *=', 'LSHIFTEQUAL <<=',
          'RSHIFTEQUAL >>=', 'URSHIFTEQUAL >>>=', 'ANDEQUAL &=', 'MODEQUAL %=',
          'XOREQUAL ^=', 'OREQUAL |=',
          ]
         ),
    ), (
        'punctuators_various_others',
        ('. , ; : + - * % & | ^ ~ ? ! ( ) { } [ ]',
         ['PERIOD .', 'COMMA ,', 'SEMI ;', 'COLON :', 'PLUS +', 'MINUS -',
          'MULT *', 'MOD %', 'BAND &', 'BOR |', 'BXOR ^', 'BNOT ~',
          'CONDOP ?', 'NOT !', 'LPAREN (', 'RPAREN )', 'LBRACE {', 'RBRACE }',
          'LBRACKET [', 'RBRACKET ]']
         ),
    ), (
        'division_simple',
        ('a / b', ['ID a', 'DIV /', 'ID b']),
    ), (
        'numbers',
        (('3 3.3 0 0. 0.0 0.001 010 3.e2 3.e-2 3.e+2 3E2 3E+2 3E-2 '
          '0.5e2 0.5e+2 0.5e-2 33 128.15 0x001 0X12ABCDEF 0xabcdef'),
         ['NUMBER 3', 'NUMBER 3.3', 'NUMBER 0', 'NUMBER 0.', 'NUMBER 0.0',
          'NUMBER 0.001', 'NUMBER 010', 'NUMBER 3.e2', 'NUMBER 3.e-2',
          'NUMBER 3.e+2', 'NUMBER 3E2', 'NUMBER 3E+2', 'NUMBER 3E-2',
          'NUMBER 0.5e2', 'NUMBER 0.5e+2', 'NUMBER 0.5e-2', 'NUMBER 33',
          'NUMBER 128.15', 'NUMBER 0x001', 'NUMBER 0X12ABCDEF',
          'NUMBER 0xabcdef']
         ),
    ), (
        'strings_simple_quote',
        (""" '"' """, ["""STRING '"'"""]),
    ), (
        'strings_escape_quote_tab',
        (r'''"foo" 'foo' "x\";" 'x\';' "foo\tbar"''',
         ['STRING "foo"', """STRING 'foo'""", r'STRING "x\";"',
          r"STRING 'x\';'", r'STRING "foo\tbar"']
         ),
    ), (
        'strings_escape_ascii',
        (r"""'\x55' "\x12ABCDEF" '!@#$%^&*()_+{}[]\";?'""",
         [r"STRING '\x55'", r'STRING "\x12ABCDEF"',
          r"STRING '!@#$%^&*()_+{}[]\";?'"]
         ),
    ), (
        'strings_escape_unicode',
        (r"""'\u0001' "\uFCEF" 'a\\\b\n'""",
         [r"STRING '\u0001'", r'STRING "\uFCEF"', r"STRING 'a\\\b\n'"]
         ),
    ), (
        'strings_unicode',
        (u'"тест строки\\""', [u'STRING "тест строки\\""']),
    ), (
        'strings_escape_octal',
        (r"""'\251'""", [r"""STRING '\251'"""]),
    ), (
        # Bug - https://github.com/rspivak/slimit/issues/5
        'slimit_issue_5',
        (r"var tagRegExp = new RegExp('<(\/*)(FooBar)', 'gi');",
         ['VAR var', 'ID tagRegExp', 'EQ =',
          'NEW new', 'ID RegExp', 'LPAREN (',
          r"STRING '<(\/*)(FooBar)'", 'COMMA ,', "STRING 'gi'",
          'RPAREN )', 'SEMI ;']),
    ), (
        # same as above but inside double quotes
        'slimit_issue_5_double_quote',
        (r'"<(\/*)(FooBar)"', [r'STRING "<(\/*)(FooBar)"']),
    ), (
        # multiline string (string written across multiple lines
        # of code) https://github.com/rspivak/slimit/issues/24
        'slimit_issue_24_multi_line_code_double',
        (r"""var a = 'hello \
world'""",
         ['VAR var', 'ID a', 'EQ =', "STRING 'hello world'"]),
    ), (
        'slimit_issue_24_multi_line_code_single',
        (r'''var a = "hello \
world"''',
         ['VAR var', 'ID a', 'EQ =', 'STRING "hello world"']),
    ), (
        # # Comments
        # ("""
        # //comment
        # a = 5;
        # """, ['LINE_COMMENT //comment', 'ID a', 'EQ =', 'NUMBER 5', 'SEMI ;']
        #  ),
        # ('a//comment', ['ID a', 'LINE_COMMENT //comment']),
        # ('/***/b/=3//line',
        #  ['BLOCK_COMMENT /***/', 'ID b', 'DIVEQUAL /=',
        #   'NUMBER 3', 'LINE_COMMENT //line']
        #  ),
        # ('/*\n * Copyright LGPL 2011 \n*/\na = 1;',
        #  ['BLOCK_COMMENT /*\n * Copyright LGPL 2011 \n*/',
        #   'ID a', 'EQ =', 'NUMBER 1', 'SEMI ;']
        #  ),

        # regex
        'regex_1',
        (r'a=/a*/,1', ['ID a', 'EQ =', 'REGEX /a*/', 'COMMA ,', 'NUMBER 1']),
    ), (
        'regex_2',
        (r'a=/a*[^/]+/,1',
         ['ID a', 'EQ =', 'REGEX /a*[^/]+/', 'COMMA ,', 'NUMBER 1']
         ),
    ), (
        'regex_3',
        (r'a=/a*\[^/,1',
         ['ID a', 'EQ =', r'REGEX /a*\[^/', 'COMMA ,', 'NUMBER 1']
         ),
    ), (
        'regex_4',
        (r'a=/\//,1', ['ID a', 'EQ =', r'REGEX /\//', 'COMMA ,', 'NUMBER 1']),
    ), (
        # not a regex, just a division
        # https://github.com/rspivak/slimit/issues/6
        'slimit_issue_6_not_regex_but_division',
        (r'x = this / y;',
         ['ID x', 'EQ =', 'THIS this', r'DIV /', r'ID y', r'SEMI ;']),
    ), (
        'regex_mozilla_example_1',
        # next two are from
        # http://www.mozilla.org/js/language/js20-2002-04/rationale/syntax.html#regular-expressions
        ("""for (var x = a in foo && "</x>" || mot ? z:/x:3;x<5;y</g/i) {xyz(x++);}""",
         ["FOR for", "LPAREN (", "VAR var", "ID x", "EQ =", "ID a", "IN in",
          "ID foo", "AND &&", 'STRING "</x>"', "OR ||", "ID mot", "CONDOP ?",
          "ID z", "COLON :", "REGEX /x:3;x<5;y</g", "DIV /", "ID i",
          "RPAREN )", "LBRACE {", "ID xyz", "LPAREN (", "ID x", "PLUSPLUS ++",
          "RPAREN )", "SEMI ;", "RBRACE }"]
         ),
    ), (
        'regex_mozilla_example_2',
        ("""for (var x = a in foo && "</x>" || mot ? z/x:3;x<5;y</g/i) {xyz(x++);}""",
         ["FOR for", "LPAREN (", "VAR var", "ID x", "EQ =", "ID a", "IN in",
          "ID foo", "AND &&", 'STRING "</x>"', "OR ||", "ID mot", "CONDOP ?",
          "ID z", "DIV /", "ID x", "COLON :", "NUMBER 3", "SEMI ;", "ID x",
          "LT <", "NUMBER 5", "SEMI ;", "ID y", "LT <", "REGEX /g/i",
          "RPAREN )", "LBRACE {", "ID xyz", "LPAREN (", "ID x", "PLUSPLUS ++",
          "RPAREN )", "SEMI ;", "RBRACE }"]
         ),

    ), (
        'regex_illegal_1',
        # Various "illegal" regexes that are valid according to the std.
        (r"""/????/, /++++/, /[----]/ """,
         ['REGEX /????/', 'COMMA ,',
          'REGEX /++++/', 'COMMA ,', 'REGEX /[----]/']
         ),

    ), (
        'regex_stress_test_1',
        # Stress cases from http://stackoverflow.com/questions/5533925/what-javascript-constructs-does-jslex-incorrectly-lex/5573409#5573409
        (r"""/\[/""", [r"""REGEX /\[/"""]),
    ), (
        'regex_stress_test_2',
        (r"""/[i]/""", [r"""REGEX /[i]/"""]),
    ), (
        'regex_stress_test_3',
        (r"""/[\]]/""", [r"""REGEX /[\]]/"""]),
    ), (
        'regex_stress_test_4',
        (r"""/a[\]]/""", [r"""REGEX /a[\]]/"""]),
    ), (
        'regex_stress_test_5',
        (r"""/a[\]]b/""", [r"""REGEX /a[\]]b/"""]),
    ), (
        'regex_stress_test_6',
        (r"""/[\]/]/gi""", [r"""REGEX /[\]/]/gi"""]),
    ), (
        'regex_stress_test_7',
        (r"""/\[[^\]]+\]/gi""", [r"""REGEX /\[[^\]]+\]/gi"""]),
    ), (
        'regex_stress_test_8',
        ("""
         rexl.re = {
         NAME: /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/,
         UNQUOTED_LITERAL: /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/,
         QUOTED_LITERAL: /^'(?:[^']|'')*'/,
         NUMERIC_LITERAL: /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/,
         SYMBOL: /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/
         };
         """, [
         "ID rexl", "PERIOD .", "ID re", "EQ =", "LBRACE {",
         "ID NAME", "COLON :",
         r"""REGEX /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/""", "COMMA ,",
         "ID UNQUOTED_LITERAL", "COLON :",
         r"""REGEX /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
         "COMMA ,", "ID QUOTED_LITERAL", "COLON :",
         r"""REGEX /^'(?:[^']|'')*'/""", "COMMA ,", "ID NUMERIC_LITERAL",
         "COLON :",
         r"""REGEX /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""", "COMMA ,",
         "ID SYMBOL", "COLON :",
         r"""REGEX /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",
         "RBRACE }", "SEMI ;"]),
    ), (
        'regex_stress_test_9',
        ("""
         rexl.re = {
         NAME: /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/,
         UNQUOTED_LITERAL: /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/,
         QUOTED_LITERAL: /^'(?:[^']|'')*'/,
         NUMERIC_LITERAL: /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/,
         SYMBOL: /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/
         };
         str = '"';
         """, [
         "ID rexl", "PERIOD .", "ID re", "EQ =", "LBRACE {",
         "ID NAME", "COLON :", r"""REGEX /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/""",
         "COMMA ,", "ID UNQUOTED_LITERAL", "COLON :",
         r"""REGEX /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
         "COMMA ,", "ID QUOTED_LITERAL", "COLON :",
         r"""REGEX /^'(?:[^']|'')*'/""", "COMMA ,",
         "ID NUMERIC_LITERAL", "COLON :",
         r"""REGEX /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""", "COMMA ,",
         "ID SYMBOL", "COLON :",
         r"""REGEX /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",
         "RBRACE }", "SEMI ;",
         "ID str", "EQ =", """STRING '"'""", "SEMI ;",
         ]),
    ), (
        'regex_stress_test_10',
        (r""" this._js = "e.str(\"" + this.value.replace(/\\/g, "\\\\").replace(/"/g, "\\\"") + "\")"; """,
         ["THIS this", "PERIOD .", "ID _js", "EQ =",
          r'''STRING "e.str(\""''', "PLUS +", "THIS this", "PERIOD .",
          "ID value", "PERIOD .", "ID replace", "LPAREN (", r"REGEX /\\/g",
          "COMMA ,", r'STRING "\\\\"', "RPAREN )", "PERIOD .", "ID replace",
          "LPAREN (", r'REGEX /"/g', "COMMA ,", r'STRING "\\\""', "RPAREN )",
          "PLUS +", r'STRING "\")"', "SEMI ;"]),
    ), (
        'regex_division_check',
        ('a = /a/ / /b/',
         ['ID a', 'EQ =', 'REGEX /a/', 'DIV /', 'REGEX /b/']),
    ), (
        'for_regex_slimit_issue_54',
        ('for (;;) /r/;',
         ['FOR for', 'LPAREN (', 'SEMI ;', 'SEMI ;', 'RPAREN )',
          'REGEX /r/', 'SEMI ;']),
    ), (
        'for_regex_slimit_issue_54_not_break_division',
        ('for (;;) { x / y }',
         ['FOR for', 'LPAREN (', 'SEMI ;', 'SEMI ;', 'RPAREN )',
          'LBRACE {', 'ID x', 'DIV /', 'ID y', 'RBRACE }']),
    ), (
        'for_regex_slimit_issue_54_bracket_accessor_check',
        ('s = {a:1} + s[2] / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'ID s', 'LBRACKET [', 'NUMBER 2', 'RBRACKET ]',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_function_parentheses_check',
        ('s = {a:1} + f(2) / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'ID f', 'LPAREN (', 'NUMBER 2', 'RPAREN )',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_math_parentheses_check',
        ('s = {a:1} + (2) / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'LPAREN (', 'NUMBER 2', 'RPAREN )',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_math_bracket_check',
        ('s = {a:1} + [2] / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'LBRACKET [', 'NUMBER 2', 'RBRACKET ]',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_math_braces_check',
        ('s = {a:2} / 166 / 9',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 2',
          'RBRACE }', 'DIV /', 'NUMBER 166', 'DIV /', 'NUMBER 9'])
    ), (
        'do_while_regex',
        ('do {} while (0) /s/',
         ['DO do', 'LBRACE {', 'RBRACE }', 'WHILE while', 'LPAREN (',
          'NUMBER 0', 'RPAREN )', 'REGEX /s/'])
    ), (
        'if_regex',
        ('if (thing) /s/',
         ['IF if', 'LPAREN (', 'ID thing', 'RPAREN )', 'REGEX /s/'])
    ), (
        'identifier_math',
        ('f (v) /s/g',
         ['ID f', 'LPAREN (', 'ID v', 'RPAREN )', 'DIV /', 'ID s', 'DIV /',
          'ID g'])
    ), (
        'section_7',
        ("a = b\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'DIV /', 'ID hi', 'DIV /', 'ID s'])
    ), (
        'section_7_extras',
        ("a = b\n\n\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'DIV /', 'ID hi', 'DIV /', 'ID s'])
    ), (
        # okay this is getting ridiculous how bad ECMA is.
        'section_7_comments',
        ("a = b\n/** **/\n\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'DIV /', 'ID hi', 'DIV /', 'ID s'])
    )])
)


LexerErrorTestCase = build_exception_testcase(
    'LexerErrorTestCase', run_lex, [(
        'extra_ending_braces',
        '())))',
    )], ECMASyntaxError,
)
