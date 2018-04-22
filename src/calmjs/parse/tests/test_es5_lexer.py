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
from functools import partial

from calmjs.parse.lexers.es5 import Lexer
from calmjs.parse.exceptions import ECMASyntaxError

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase
from calmjs.parse.tests.lexer import (
    run_lexer,
    run_lexer_pos,
    es5_cases,
    es5_pos_cases,
    es5_error_cases,
)


class LexerFailureTestCase(unittest.TestCase):

    def test_illegal_unicode_char_in_identifier(self):
        lexer = Lexer()
        lexer.input(u'\u0036_tail')
        token = lexer.token()
        # \u0036_tail is the same as 6_tail and that's not a correct ID
        # Check that the token is NUMBER and not an ID
        self.assertEqual(token.type, 'NUMBER')
        self.assertEqual(token.value, '6')

    def test_bad_initial_input(self):
        lexer = Lexer()
        lexer.input(u'#')
        with self.assertRaises(ECMASyntaxError) as e:
            lexer.token()

        self.assertEqual(e.exception.args[0], "Illegal character '#' at 1:1")

    def test_extra_ending_braces(self):
        lexer = Lexer()
        lexer.input('\n\n())))')
        with self.assertRaises(ECMASyntaxError) as e:
            [token for token in lexer]
        self.assertEqual(str(e.exception), "Mismatched ')' at 3:3")


LexerKeywordTestCase = build_equality_testcase(
    'LexerKeywordTestCase', partial(run_lexer, lexer_cls=Lexer), (
        (label, data[0], data[1],) for label, data in [(
            # Keywords
            # ('break case ...', ['BREAK break', 'CASE case', ...])
            'keywords_all',
            (' '.join(kw.lower() for kw in Lexer.keywords),
             ['%s %s' % (kw, kw.lower()) for kw in Lexer.keywords]
             ),
        )]
    )
)

LexerTestCase = build_equality_testcase(
    'LexerTestCase', partial(run_lexer, lexer_cls=Lexer), (
        (label, data[0], data[1],) for label, data in es5_cases))

LexerErrorTestCase = build_exception_testcase(
    'LexerErrorTestCase', partial(
        run_lexer, lexer_cls=Lexer), es5_error_cases, ECMASyntaxError)

LexerPosTestCase = build_equality_testcase(
    'LexerPosTestCase', partial(
        run_lexer_pos, lexer_cls=Lexer), es5_pos_cases)
