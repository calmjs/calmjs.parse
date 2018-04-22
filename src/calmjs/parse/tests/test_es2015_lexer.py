# -*- coding: utf-8 -*-
import unittest
from functools import partial

from calmjs.parse.lexers.es2015 import Lexer
from calmjs.parse.exceptions import ECMASyntaxError

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.tests.lexer import (
    run_lexer,
    run_lexer_pos,
    es5_cases,
    es5_pos_cases,
    es5_all_cases,
    es2015_cases,
)


class LexerFailureTestCase(unittest.TestCase):

    def test_initial_template_character(self):
        lexer = Lexer()
        lexer.input('`')
        with self.assertRaises(ECMASyntaxError) as e:
            [token for token in lexer]
        self.assertEqual(str(e.exception), "Illegal character '`' at 1:1")


LexerKeywordTestCase = build_equality_testcase(
    'LexerTestCase', partial(run_lexer, lexer_cls=Lexer), (
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

LexerES5TestCase = build_equality_testcase(
    'LexerES5TestCase', partial(run_lexer, lexer_cls=Lexer), (
        (label, data[0], data[1],) for label, data in es5_cases))

LexerES5PosTestCase = build_equality_testcase(
    'LexerES5PosTestCase', partial(
        run_lexer_pos, lexer_cls=Lexer), es5_pos_cases)

LexerES5AllTestCase = build_equality_testcase(
    'LexerES5AllTestCase', partial(run_lexer, lexer_cls=partial(
        Lexer, yield_comments=True
    )), ((label, data[0], data[1],) for label, data in es5_all_cases))

LexerES2015TestCase = build_equality_testcase(
    'LexerES2015TestCase', partial(run_lexer, lexer_cls=Lexer), (
        (label, data[0], data[1],) for label, data in es2015_cases))
