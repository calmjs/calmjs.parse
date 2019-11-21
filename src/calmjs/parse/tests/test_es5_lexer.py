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
import textwrap
from functools import partial

from calmjs.parse.lexers.es5 import Lexer
from calmjs.parse.exceptions import ECMASyntaxError

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase
from calmjs.parse.tests.lexer import (
    run_lexer,
    run_lexer_pos,
    es5_cases,
    es5_all_cases,
    es5_pos_cases,
    es5_error_cases_str_sq,
    es5_error_cases_str_dq,
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


class LexerGeneralTestCase(unittest.TestCase):

    def test_backtracking_div_default(self):
        # this test emulates what appear to happens when the parser
        # backtracks upon encountering the `/` that it can't parse.
        lexer = Lexer()
        lexer.input('{}/a/')
        self.assertEqual(lexer.next().type, 'LBRACE')
        self.assertEqual(lexer.next().type, 'RBRACE')
        self.assertEqual(lexer.next().type, 'DIV')

        token = lexer.backtracked_token()
        self.assertEqual(('REGEX', '/a/'), (token.type, token.value))

    def test_backtracking_multiple(self):
        # Although dealing with additional tokens like comments and
        # newlines are not done (i.e. they don't get backtracked), it
        # should not cause additional issues
        lexer = Lexer()
        lexer.input('{}\n/a/')
        self.assertEqual(lexer.next().type, 'LBRACE')
        self.assertEqual(lexer.next().type, 'RBRACE')
        self.assertEqual(lexer.next().type, 'DIV')

        token = lexer.backtracked_token(pos=2)
        self.assertEqual(('REGEX', '/a/'), (token.type, token.value))


class LexerWithCommentsTestCase(unittest.TestCase):

    def test_with_line_comments_before(self):
        lexer = Lexer(with_comments=True)
        lexer.input(textwrap.dedent('''
        // foo
        // bar
        baz
        '''))
        tokens = [token for token in lexer]
        self.assertEqual(1, len(tokens))
        token = tokens[0]
        self.assertEqual(2, len(token.hidden_tokens))
        self.assertEqual(token.hidden_tokens[0].value, '// foo')
        self.assertEqual(token.hidden_tokens[0].type, 'LINE_COMMENT')
        self.assertEqual(token.hidden_tokens[1].value, '// bar')
        self.assertEqual(token.hidden_tokens[1].type, 'LINE_COMMENT')

    def test_with_line_comment_trail(self):
        lexer = Lexer(with_comments=True)
        lexer.input(textwrap.dedent('''
        baz // bar
        foo
        '''))
        tokens = [token for token in lexer]
        self.assertEqual(2, len(tokens))
        self.assertFalse(hasattr(tokens[0], 'hidden_tokens'))
        token = tokens[1]
        self.assertEqual(1, len(token.hidden_tokens))
        self.assertEqual(token.hidden_tokens[0].value, '// bar')
        self.assertEqual(token.hidden_tokens[0].type, 'LINE_COMMENT')

    def test_block_comment(self):
        lexer = Lexer(with_comments=True)
        lexer.input(textwrap.dedent('''
        baz /*foo
        *// // bar
        '''))
        tokens = [token for token in lexer]
        self.assertEqual(2, len(tokens))
        self.assertFalse(hasattr(tokens[0], 'hidden_tokens'))
        token = tokens[1]
        self.assertEqual(1, len(token.hidden_tokens))
        self.assertEqual(token.hidden_tokens[0].value, '/*foo\n*/')
        self.assertEqual(token.hidden_tokens[0].type, 'BLOCK_COMMENT')
        # the remaining comments remain on lexer
        self.assertEqual(lexer.hidden_tokens[0].value, '// bar')


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

LexerAllTestCase = build_equality_testcase(
    'LexerAllTestCase', partial(run_lexer, lexer_cls=partial(
        Lexer, yield_comments=True
    )), ((label, data[0], data[1],) for label, data in es5_all_cases))

LexerErrorTestCase = build_exception_testcase(
    'LexerErrorTestCase', partial(
        run_lexer, lexer_cls=Lexer), es5_error_cases_str_sq, ECMASyntaxError)

LexerErrorStrDQTestCase = build_exception_testcase(
    'LexerErrorStrDQTestCase', partial(
        run_lexer, lexer_cls=Lexer), es5_error_cases_str_dq, ECMASyntaxError)

LexerPosTestCase = build_equality_testcase(
    'LexerPosTestCase', partial(
        run_lexer_pos, lexer_cls=Lexer), es5_pos_cases)
