# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import textwrap
import unittest
from io import StringIO

from calmjs.parse import asttypes
from calmjs.parse.parsers.es5 import Parser
from calmjs.parse.parsers.es5 import parse
from calmjs.parse.parsers.es5 import read
from calmjs.parse.unparsers.es5 import pretty_print
from calmjs.parse.walkers import walk

from calmjs.parse.tests.parser import (
    ParserCaseMixin,
    build_node_repr_test_cases,
    build_asi_test_cases,
    build_syntax_error_test_cases,
    build_regex_syntax_error_test_cases,
    build_comments_test_cases,
)


class ParserTestCase(unittest.TestCase, ParserCaseMixin):

    parse = staticmethod(parse)

    def test_modify_tree(self):
        text = """
        for (var i = 0; i < 10; i++) {
          var x = 5 + i;
        }
        """
        parser = Parser()
        tree = parser.parse(text)
        for node in walk(tree):
            if isinstance(node, asttypes.Identifier) and node.value == 'i':
                node.value = 'hello'
        self.assertMultiLineEqual(
            str(tree),
            textwrap.dedent("""
            for (var hello = 0; hello < 10; hello++) {
              var x = 5 + hello;
            }
            """).lstrip()
        )

    def test_read(self):
        stream = StringIO('var foo = "bar";')
        node = read(stream)
        self.assertTrue(isinstance(node, asttypes.ES5Program))
        self.assertIsNone(node.sourcepath)

        stream.name = 'somefile.js'
        node = read(stream)
        self.assertEqual(node.sourcepath, 'somefile.js')


ParsedNodeTypeTestCase = build_node_repr_test_cases(
    'ParsedNodeTypeTestCase', parse, 'ES5Program')

# ASI - Automatic Semicolon Insertion
ParserToECMAASITestCase = build_asi_test_cases(
    'ParserToECMAASITestCase', parse, pretty_print)

ECMASyntaxErrorsTestCase = build_syntax_error_test_cases(
    'ECMASyntaxErrorsTestCase', parse)

ECMARegexSyntaxErrorsTestCase = build_regex_syntax_error_test_cases(
    'ECMARegexSyntaxErrorsTestCase', parse)

ParsedNodeTypesWithCommentsTestCase = build_comments_test_cases(
    'ParsedNodeTypeWithCommentsTestCase', parse, 'ES5Program')
