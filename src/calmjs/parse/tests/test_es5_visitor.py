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

__author__ = 'Ruslan Spivak <ruslan.spivak@gmail.com>'

import textwrap
import unittest

from calmjs.parse.asttypes import Node
from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.parsers.es5 import Parser
from calmjs.parse.visitors.generic import NodeVisitor
from calmjs.parse.visitors.es5 import PrettyPrinter as ECMAVisitor

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase

parser = Parser()


class BaseTestCase(unittest.TestCase):

    def test_default(self):
        self.assertTrue(ECMAVisitor().visit(Node()).startswith('GEN: '))


def parse_to_ecma(value):
    return str(parser.parse(value))


def parse_force_parens_to_ecma(value):
    # Parse, then walk through all nodes and force parens
    tree = parser.parse(value)
    for node in NodeVisitor().visit(tree):
        node._parens = True
    return str(tree)


ECMAVisitorTestCase = build_equality_testcase(
    'ECMAVisitorTestCase', parse_to_ecma, ((
        label, value, value,
    ) for label, value in ((
        label,
        textwrap.dedent(value).strip(),
    ) for label, value in [(
        'block',
        """
        {
          var a = 5;
        }
        """,
    ), (
        'variable_statement',
        """
        var a;
        var b;
        var a, b = 3;
        var a = 1, b;
        var a = 5, b = 7;
        """,
    ), (
        'empty_statement',
        """
        ;
        ;
        ;
        """,
    ), (
        'if_statement_inline',
        'if (true) var x = 100;',
    ), (
        'if_statement_block',
        """
        if (true) {
          var x = 100;
          var y = 200;
        }
        """,
    ), (
        'if_else_inline',
        'if (true) if (true) var x = 100; else var y = 200;',
    ), (
        'if_else_block',
        """
        if (true) {
          var x = 100;
        } else {
          var y = 200;
        }
        """,
    ), (
        ################################
        # iteration
        ################################

        'iteration_reuse',
        """
        for (i = 0; i < 10; i++) {
          x = 10 * i;
        }
        """,
    ), (
        'iteration_var',
        """
        for (var i = 0; i < 10; i++) {
          x = 10 * i;
        }
        """,
    ), (
        'iteration_multi_value',
        """
        for (i = 0, j = 10; i < j && j < 15; i++, j++) {
          x = i * j;
        }
        """,
    ), (
        'iteration_multi_var_value',
        """
        for (var i = 0, j = 10; i < j && j < 15; i++, j++) {
          x = i * j;
        }
        """,
    ), (
        'iteration_in',
        """
        for (p in obj) {

        }
        """,
    ), (
        # retain the semicolon in the initialiser part of a 'for' statement
        'iteration_conditional_initialiser',
        """
        for (Q || (Q = []); d < b; ) {
          d = 1;
        }
        """,
    ), (
        'iteration_new_object',
        """
        for (new Foo(); d < b; ) {
          d = 1;
        }
        """,
    ), (
        'iteration_ternary_initializer',
        """
        for (2 >> (foo ? 32 : 43) && 54; 21; ) {
          a = c;
        }
        """,
    ), (
        'iteration_regex_initialiser',
        """
        for (/^.+/g; cond(); ++z) {
          ev();
        }
        """,
    ), (
        'iteration_var_in_obj',
        """
        for (var p in obj) {
          p = 1;
        }
        """,
    ), (
        'iteration_do_while',
        """
        do {
          x += 1;
        } while (true);
        """,
    ), (
        'while_loop',
        """
        while (false) {
          x = null;
        }
        """,
    ), (
        # test 15
        ################################
        # continue statement
        ################################

        'while_loop_continue',
        """
        while (true) {
          continue;
          s = 'I am not reachable';
        }
        """,
    ), (
        'while_loop_continue_label',
        """
        while (true) {
          continue label1;
          s = 'I am not reachable';
        }
        """,
    ), (
        ################################
        # break statement
        ################################
        'while_loop_break',
        """
        while (true) {
          break;
          s = 'I am not reachable';
        }
        """,
        # test 18
    ), (
        'while_loop_break_label',
        """
        while (true) {
          break label1;
          s = 'I am not reachable';
        }
        """,
    ), (
        ################################
        # return statement
        ################################

        'return_empty',
        """
        {
          return;
        }
        """,
    ), (
        'return_1',
        """
        {
          return 1;
        }
        """,
    ), (
        # test21
        ################################
        # with statement
        ################################
        'with_statement',
        """
        with (x) {
          var y = x * 2;
        }
        """,
    ), (
        ################################
        # labelled statement
        ################################

        'labelled_statement',
        """
        label: while (true) {
          x *= 3;
        }
        """,

    ), (
        ################################
        # switch statement
        ################################
        'switch_statement',
        """
        switch (day_of_week) {
          case 6:
          case 7:
            x = 'Weekend';
            break;
          case 1:
            x = 'Monday';
            break;
          default:
            break;
        }
        """,

    ), (
        # test 24
        ################################
        # throw statement
        ################################
        'throw_statement',
        """
        throw 'exc';
        """,

    ), (
        ################################
        # debugger statement
        ################################
        'debugger_statement',
        'debugger;',

    ), (
        ################################
        # expression statement
        ################################
        'expression_statement',
        """
        5 + 7 - 20 * 10;
        ++x;
        --x;
        x++;
        x--;
        x = 17 /= 3;
        s = mot ? z : /x:3;x<5;y</g / i;
        """,

    ), (
        # test 27
        ################################
        # try statement
        ################################
        'try_catch_statement',
        """
        try {
          x = 3;
        } catch (exc) {
          x = exc;
        }
        """,

    ), (
        'try_finally_statement',
        """
        try {
          x = 3;
        } finally {
          x = null;
        }
        """,

    ), (
        'try_catch_finally_statement',
        """
        try {
          x = 5;
        } catch (exc) {
          x = exc;
        } finally {
          y = null;
        }
        """,

    ), (
        # test 30
        ################################
        # function
        ################################
        'function_with_arguments',
        """
        function foo(x, y) {
          z = 10;
          return x + y + z;
        }
        """,

    ), (
        'function_without_arguments',
        """
        function foo() {
          return 10;
        }
        """,

    ), (
        'var_function_without_arguments',
        """
        var a = function() {
          return 10;
        };
        """,
    ), (
        # test 33
        'var_function_with_arguments',
        """
        var a = function foo(x, y) {
          return x + y;
        };
        """,
    ), (
        # nested function declaration
        'function_nested_declaration',
        """
        function foo() {
          function bar() {

          }
        }
        """,

    ), (
        'function_immediate_execution',
        """
        var mult = function(x) {
          return x * 10;
        }();
        """,

    ), (
        # function call
        # test 36
        'function_call',
        'foo();',
    ), (
        'function_call_argument',
        'foo(x, 7);',
    ), (
        'function_call_access_element',
        'foo()[10];',
    ), (
        'function_call_access_attribute',
        'foo().foo;',
    ), (
        'new_keyword',
        'var foo = new Foo();',
    ), (
        # dot accessor
        'new_keyword_dot_accessor',
        'var bar = new Foo.Bar();',

    ), (
        # bracket accessor
        'new_keyword_bracket_accessor',
        'var bar = new Foo.Bar()[7];',

    ), (
        # object literal
        'object_literal_litearl_keys',
        """
        var obj = {
          foo: 10,
          bar: 20
        };
        """,
    ), (
        'object_literal_numeric_keys',
        """
        var obj = {
          1: 'a',
          2: 'b'
        };
        """,
    ), (
        'object_literal_string_keys',
        """
        var obj = {
          'a': 100,
          'b': 200
        };
        """,
    ), (
        'object_literal_empty',
        """
        var obj = {
        };
        """,
    ), (
        # array
        'array_create_access',
        """
        var a = [1,2,3,4,5];
        var res = a[3];
        """,
    ), (
        # elision
        'elision_1',
        'var a = [,,,];',
    ), (
        'elision_2',
        'var a = [1,,,4];',
    ), (
        'elision_3',
        'var a = [1,,3,,5];',

    ), (
        # test 51
        'function_definition',
        """
        String.prototype.foo = function(data) {
          var tmpl = this.toString();
          return tmpl.replace(/{{\s*(.*?)\s*}}/g, function(a, b) {
            var node = data;
            if (true) {
              var value = true;
            } else {
              var value = false;
            }
            $.each(n.split('.'), function(i, sym) {
              node = node[sym];
            });
            return node;
          });
        };
        """,
    ), (
        'dot_accessor_integer',
        """
        (0x25).toString();
        (1e3).toString();
        (25).toString();
        """,
    ), (
        'attr_accessor_integer',
        """
        0x25["toString"]();
        1e3["toString"]();
        25["toString"]();
        """,
    ), (

        #######################################
        # Make sure parentheses are not removed
        #######################################

        # ... Expected an identifier and instead saw '/'
        'parentheses_not_removed',
        r'Expr.match[type].source + (/(?![^\[]*\])(?![^\(]*\))/.source);',

    ), (
        'comparison',
        '(options = arguments[i]) != null;',

        # test 54
    ), (
        'regex_test',
        'return (/h\d/i).test(elem.nodeName);',

    ), (
        # https://github.com/rspivak/slimit/issues/42
        'slimit_issue_42',
        """
        e.b(d) ? (a = [c.f(j[1])], e.fn.attr.call(a, d, !0)) : a = [k.f(j[1])];
        """,

    ), (
        'closure_scope',
        """
        (function() {
          x = 5;
        }());
        """,

    ), (
        'return_statement_negation',
        'return !(match === true || elem.getAttribute("classid") !== match);',

    ), (
        # test 57
        'ternary_dot_accessor',
        'var el = (elem ? elem.ownerDocument || elem : 0).documentElement;',

    ), (
        # typeof
        'typeof',
        'typeof second.length === "number";',

    ), (
        # function call in FOR init
        'function_call_in_for_init',
        """
        for (o(); i < 3; i++) {

        }
        """,

    ), (
        # https://github.com/rspivak/slimit/issues/32
        'slimit_issue_32',
        """
        Name.prototype = {
          get fullName() {
            return this.first + " " + this.last;
          },
          set fullName(name) {
            var names = name.split(" ");
            this.first = names[0];
            this.last = names[1];
          }
        };
        """,
    ), (
        'dot_accessor_on_integer',
        """
        (0).toString();
        """,
    )]))
)


ECMAVisitorWithParensTestCase = build_equality_testcase(
    'ECMAVisitorWithParensTestCase', parse_force_parens_to_ecma, ((
        label,
        textwrap.dedent(source).strip(),
        textwrap.dedent(answer).strip(),
    ) for label, source, answer in [(
        'dot_accessor',
        """
        value = this.value;
        """,
        """
        (value = (this.value));
        """,
    ), (
        'ternary_conditional',
        """
        x ? y : z;
        """,
        """
        (x ? y : z);
        """,
    ), (
        'unary_operator',
        """
        !true;
        """,
        """
        (!true);
        """,
    ), (
        'function_wrap',
        """
        var foo = function() {

        };
        """,
        """
        var foo = (function() {

        });
        """,
    ), (
        'prop_get_set',
        """
        Name.prototype = {
          get fullName() {
            return this.first + " " + this.last;
          },
          set fullName(name) {
            var names = name.split(" ");
            this.first = names[0];
            this.last = names[1];
          }
        };
        """,
        """
        ((Name.prototype) = {
          (get fullName() {
            return (((this.first) + " ") + (this.last));
          }),
          (set fullName(name) {
            var names = ((name.split)(" "));
            ((this.first) = names[0]);
            ((this.last) = names[1]);
          })
        });
        """,
    )])
)


ECMASyntaxErrorTestCase = build_exception_testcase(
    'ECMAVisitorTestCase', parse_to_ecma, ((
        label,
        textwrap.dedent(argument).strip(),
    ) for label, argument in [(
        'get_no_argument',
        """
        Name.prototype = {
          get something(fail) {
            return false;
          }
        }
        """
    ), (
        'set_too_many_arguments',
        """
        Name.prototype = {
          set failure(arg1, arg2) {
            return false;
          }
        };
        """,
    ), (
        'numeric_bare_accessor',
        """
        var x = 0.toString();
        """,
    )]), ECMASyntaxError
)


class SpecialTestCase(unittest.TestCase):
    """
    For catching special case
    """

    def test_repr_failure_message(self):
        with self.assertRaises(ECMASyntaxError) as e:
            parse_to_ecma("""Name.prototype = {
              set failure(arg1, arg2) {
                return {1:{2:{3:{4:4}}}};
              }
            };""")

        self.assertEqual(e.exception.args[0], textwrap.dedent("""
        Setter functions must have one argument: <SetPropAssign elements=[
          <Return expr=<Object properties=[
            <Assign ...>
          ]>>
        ], parameters=[
          <Identifier value='arg1'>,
          <Identifier value='arg2'>
        ], prop_name=<Identifier value='failure'>>
        """).strip())
