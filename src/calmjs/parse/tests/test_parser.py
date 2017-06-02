###############################################################################
#
# Copyright (c) 2011-2012 Ruslan Spivak
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

import textwrap
import unittest

from calmjs.parse import asttypes
from calmjs.parse.parser import Parser
from calmjs.parse.visitors import nodevisitor

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase


class ParserTestCase(unittest.TestCase):

    def test_line_terminator_at_the_end_of_file(self):
        parser = Parser()
        parser.parse('var $_ = function(x){}(window);\n')

    # XXX: function expression ?
    def test_function_expression(self):
        text = """
        if (true) {
          function() {
            foo;
            location = 'http://anywhere.com';
          }
        }
        """
        parser = Parser()
        parser.parse(text)

    def test_modify_tree(self):
        text = """
        for (var i = 0; i < 10; i++) {
          var x = 5 + i;
        }
        """
        parser = Parser()
        tree = parser.parse(text)
        for node in nodevisitor.visit(tree):
            if isinstance(node, asttypes.Identifier) and node.value == 'i':
                node.value = 'hello'
        self.assertMultiLineEqual(
            tree.to_ecma(),
            textwrap.dedent("""
            for (var hello = 0; hello < 10; hello++) {
              var x = 5 + hello;
            }
            """).strip()
        )

    def test_bug_no_semicolon_at_the_end_of_block_plus_newline_at_eof(self):
        # https://github.com/rspivak/slimit/issues/3
        text = textwrap.dedent("""
        function add(x, y) {
          return x + y;
        }
        """)
        parser = Parser()
        tree = parser.parse(text)
        self.assertTrue(bool(tree.children()))

    def test_function_expression_is_part_of_member_expr_nobf(self):
        # https://github.com/rspivak/slimit/issues/22
        # The problem happened to be that function_expr was not
        # part of member_expr_nobf rule
        text = 'window.done_already || function () { return "slimit!" ; }();'
        self.assertTrue(bool(Parser().parse(text).children()))

    # https://github.com/rspivak/slimit/issues/29
    def test_that_parsing_eventually_stops(self):
        text = """var a;
        , b;"""
        parser = Parser()
        self.assertRaises(SyntaxError, parser.parse, text)


parser = Parser()


def regenerate(value):
    return parser.parse(value).to_ecma()


ParserToECMATestCase = build_equality_testcase(
    'ParserToECMATestCase', regenerate, ((
        label,
        textwrap.dedent(argument).strip(),
        textwrap.dedent(result).strip(),
    ) for label, argument, result in [(
        'switch_case_statement',
        """
        switch (day) {
          case 1:
            result = 'Mon';
            break
          case 2:
            break
        }
        """,
        """
        switch (day) {
          case 1:
            result = 'Mon';
            break;
          case 2:
            break;
        }
        """
    ), (
        'switch_case_statement_with_default',
        """
        switch (day) {
          case 1:
            result = 'Mon';
            break
          default:
            break
        }
        """,
        """
        switch (day) {
          case 1:
            result = 'Mon';
            break;
          default:
            break;
        }
        """
    ), (
        'while_continue',
        """
        while (true)
          continue
        a = 1;
        """,
        """
        while (true) continue;
        a = 1;
        """
    ), (
        'naked_return',
        """
        return
        a;
        """,
        """
        return;
        a;
        """
    ), (
        'assignment',
        """
        x = 5
        """,
        """
        x = 5;
        """
    ), (
        'var_declaration',
        """
        var a, b
        var x
        """,
        """
        var a, b;
        var x;
        """
    ), (
        'var_assignment',
        """
        var a = 1, b = 2
        var x = 3
        """,
        """
        var a = 1, b = 2;
        var x = 3;
        """
    ), (
        'return_auto_semi',
        """
        return
        a + b
        """,
        """
        return;
        a + b;
        """
    ), (
        'identifiers',
        """
        [true, false, null, undefined];
        """,
        """
        [true,false,null,undefined];
        """
    ), (
        'while_empty',
        """
        while (true) ;
        """,
        """
        while (true) ;
        """
    ), (
        'if_statement',
        """
        if (x) {
          y()
        }
        """,
        """
        if (x) {
          y();
        }
        """
    ), (
        'for_loop_first_empty',
        """
        for ( ; i < length; i++) {
        }
        """,
        """
        for ( ; i < length; i++) {

        }
        """
    ), (
        'for_loop_standard_declaration',
        """
        var i;
        for (i; i < length; i++) {
        }
        """,
        """
        var i;
        for (i; i < length; i++) {

        }
        """
    ), (
        # A standard test for object notation.
        'standard_object_notation',
        """
        var o = {dummy: 1}
        """,
        """
        var o = {
          dummy: 1
        };
        """
    ), (
        # issue #59
        'dot_reserved_word',
        """
        var f = function(e) {
          return e.default;
        };
        """,
        """
        var f = function(e) {
          return e.default;
        };
        """
    ), (
        # also test that the Object notation will work with reserved
        # keywords
        'property_names_with_reserved_word',
        """
        var o = {
          case: '', default: '', switch: '',
          catch: '', finally: '', try: '',
        }
        """,
        """
        var o = {
          case: '',
          default: '',
          switch: '',
          catch: '',
          finally: '',
          try: ''
        };
        """
    ), (
        # exception handling
        'try_catch_finally',
        """
        try {
          x / 0;
        }
        catch (e) {
        }
        finally {
        }
        """,
        """
        try {
          x / 0;
        } catch (e) {

        } finally {

        }
        """
    )])
)


ASISyntaxErrorsTestCase = build_exception_testcase(
    'ASISyntaxErrorsTestCase', parser.parse, ((
        label,
        textwrap.dedent(argument).strip(),
    ) for label, argument in [(
        # expression is not optional in throw statement
        # ASI at lexer level should insert ';' after throw
        'throw_error',
        """
        throw
          'exc';
        """
    )]), SyntaxError
)
