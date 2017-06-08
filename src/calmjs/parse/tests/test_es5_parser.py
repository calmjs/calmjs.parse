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
from calmjs.parse import es5
from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.exceptions import ECMARegexSyntaxError
from calmjs.parse.parsers.es5 import Parser
from calmjs.parse.visitors import generic
from calmjs.parse.visitors.es5 import pretty_print

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase


class ParserTestCase(unittest.TestCase):

    def test_line_terminator_at_the_end_of_file(self):
        parser = Parser()
        parser.parse('var $_ = function(x){}(window);\n')

    def test_bad_char_error(self):
        parser = Parser()
        with self.assertRaises(ECMASyntaxError) as e:
            parser.parse('var\x01 blagh = 1;')
        self.assertEqual(
            e.exception.args[0],
            "Illegal character '\\x01' at 1:3 after LexToken(VAR,'var',1,0)"
        )

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
        for node in generic.visit(tree):
            if isinstance(node, asttypes.Identifier) and node.value == 'i':
                node.value = 'hello'
        self.assertMultiLineEqual(
            str(tree),
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
        self.assertRaises(ECMASyntaxError, parser.parse, text)

    def test_ecma_262_whitespace_slimt_issue_84(self):
        text = u'''\uFEFF
        var foo = function() {
        // a salad of whitespaces
        \x09\r\n\x0b\x0c\x20\xa0
        \u1680\u2000\u2001\u2005\u200A
        \u2028\u2029\u202F\u205F\u3000
            return 1;
        };
        '''
        self.assertTrue(bool(Parser().parse(text).children()))


repr_visitor = generic.ReprVisitor()


def parse_to_repr(value):
    return repr_visitor.visit(es5(value))


def singleline(s):
    def clean(f):
        r = f.strip()
        return r + ' ' if r[-1:] == ',' else r
    return ''.join(clean(t) for t in textwrap.dedent(s).splitlines())


ParsedNodeTypeTestCase = build_equality_testcase(
    'ParsedNodeTypeTestCase', parse_to_repr, ((
        label,
        textwrap.dedent(argument).strip(),
        singleline(result),
    ) for label, argument, result in [(
        'block',
        """
        {
          var a = 5;
        }
        """,
        """
        <ES5Program ?children=[<Block ?children=[
          <VarStatement ?children=[<VarDecl identifier=<Identifier value='a'>,
            initializer=<Number value='5'>>]>
        ]>]>
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
        """
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>, initializer=None>
          ]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='b'>, initializer=None>
          ]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>, initializer=None>,
            <VarDecl identifier=<Identifier value='b'>, initializer=<
              Number value='3'>>
          ]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>,
              initializer=<Number value='1'>>,
            <VarDecl identifier=<Identifier value='b'>, initializer=None>
          ]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>, initializer=<
              Number value='5'>>,
            <VarDecl identifier=<Identifier value='b'>, initializer=<
              Number value='7'>>
          ]>
        ]>
        """,
    ), (
        'empty_statement',
        """
        ;
        ;
        ;
        """,
        """
        <ES5Program ?children=[
          <EmptyStatement value=';'>,
          <EmptyStatement value=';'>,
          <EmptyStatement value=';'>
        ]>
        """,
    ), (
        'if_statement_inline',
        'if (true) var x = 100;',
        """
        <ES5Program ?children=[<If alternative=None,
          consequent=<VarStatement ?children=[
            <VarDecl identifier=<Identifier value='x'>,
              initializer=<Number value='100'>>
          ]>, predicate=<Boolean value='true'>>
        ]>
        """,
    ), (
        'if_statement_block',
        """
        if (true) {
          var x = 100;
          var y = 200;
        }
        """,
        """
        <ES5Program ?children=[<If alternative=None,
          consequent=<Block ?children=[
            <VarStatement ?children=[
              <VarDecl identifier=<Identifier value='x'>,
                initializer=<Number value='100'>>
            ]>,
            <VarStatement ?children=[
              <VarDecl identifier=<Identifier value='y'>,
                initializer=<Number value='200'>>
            ]>
          ]>,
          predicate=<Boolean value='true'>>
        ]>
        """,
    ), (
        'if_else_inline',
        'if (true) if (true) var x = 100; else var y = 200;',
        """
        <ES5Program ?children=[<
          If alternative=None,
          consequent=<If alternative=<VarStatement ?children=[
            <VarDecl identifier=<Identifier value='y'>,
              initializer=<Number value='200'>>
            ]>,
            consequent=<VarStatement ?children=[
              <VarDecl identifier=<Identifier value='x'>,
                initializer=<Number value='100'>>
            ]>,
            predicate=<Boolean value='true'>>,
          predicate=<Boolean value='true'>>
        ]>
        """,
    ), (
        'if_else_block',
        """
        if (true) {
          var x = 100;
        } else {
          var y = 200;
        }
        """,
        """
        <ES5Program ?children=[
          <If alternative=<Block ?children=[
            <VarStatement ?children=[
              <VarDecl identifier=<Identifier value='y'>,
                initializer=<Number value='200'>>
            ]>
          ]>, consequent=<Block ?children=[
            <VarStatement ?children=[
              <VarDecl identifier=<Identifier value='x'>,
                initializer=<Number value='100'>>
            ]>
          ]>, predicate=<Boolean value='true'>>
        ]>
        """,
    ), (
        'iteration_var',
        """
        for (var i = 0; i < 10; i++) {
          x = 10 * i;
        }
        """,
        """
        <ES5Program ?children=[
          <For cond=<BinOp left=<Identifier value='i'>, op='<', right=<
            Number value='10'>>, count=<
              UnaryOp op='++', postfix=True, value=<Identifier value='i'>>,
            init=<VarStatement ?children=[
              <VarDecl identifier=<Identifier value='i'>,
                initializer=<Number value='0'>>
            ]>, statement=<Block ?children=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='=', right=<BinOp left=<Number value='10'>, op='*',
                  right=<Identifier value='i'>>>>
            ]
          >>
        ]>
        """,
    ), (
        'iteration_multi_value',
        """
        for (i = 0, j = 10; i < j && j < 15; i++, j++) {
          x = i * j;
        }
        """,
        """
        <ES5Program ?children=[<For cond=<BinOp left=<BinOp left=<
          Identifier value='i'>, op='<', right=<Identifier value='j'>>,
          op='&&', right=<BinOp left=<Identifier value='j'>, op='<', right=<
            Number value='15'>>>,
          count=<Comma left=<UnaryOp op='++', postfix=True, value=<
            Identifier value='i'>>, right=<UnaryOp op='++', postfix=True
            , value=<Identifier value='j'>>>,
          init=<Comma left=<Assign left=<Identifier value='i'>,
            op='=', right=<Number value='0'>>, right=<Assign left=<
              Identifier value='j'>, op='=', right=<Number value='10'>>>,
          statement=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>, op='=',
              right=<BinOp left=<Identifier value='i'>, op='*',
              right=<Identifier value='j'>>>>
          ]>>
        ]>
        """,

    ), (
        'iteration_in',
        """
        for (p in obj) {

        }
        """,
        """
        <ES5Program ?children=[
          <ForIn item=<Identifier value='p'>,
            iterable=<Identifier value='obj'>, statement=<Block >>
        ]>
        """,
    ), (
        # retain the semicolon in the initialiser part of a 'for' statement
        'iteration_conditional_initialiser',
        """
        for (Q || (Q = []); d < b; ) {
          d = 1;
        }
        """,
        """
        <ES5Program ?children=[<For cond=<BinOp left=<Identifier value='d'>,
          op='<', right=<Identifier value='b'>>, count=None,
          init=<BinOp left=<Identifier value='Q'>, op='||',
            right=<Assign left=<Identifier value='Q'>, op='=',
              right=<Array items=[]>>>,
          statement=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='d'>,
              op='=', right=<Number value='1'>>>
          ]>>
        ]>
        """,
    ), (
        'iteration_ternary_initializer',
        """
        for (2 >> (foo ? 32 : 43) && 54; 21; ) {
          a = c;
        }
        """,
        """
        <ES5Program ?children=[<For cond=<Number value='21'>, count=None,
          init=<BinOp left=<BinOp left=<Number value='2'>, op='>>', right=<
            Conditional alternative=<Number value='43'>,
            consequent=<Number value='32'>,
            predicate=<Identifier value='foo'>>>, op='&&',
            right=<Number value='54'>>, statement=<
              Block ?children=[
                <ExprStatement expr=<Assign left=<Identifier value='a'>,
                  op='=', right=<Identifier value='c'>>>
              ]>>
        ]>
        """,
    ), (
        'iteration_regex_initialiser',
        """
        for (/^.+/g; cond(); ++z) {
          ev();
        }
        """,
        """
        <ES5Program ?children=[
          <For cond=<FunctionCall args=[],
            identifier=<Identifier value='cond'>>,
            count=<UnaryOp op='++', postfix=False,
            value=<Identifier value='z'>>,
            init=<Regex value='/^.+/g'>,
            statement=<Block ?children=[
              <ExprStatement expr=<FunctionCall args=[],
                identifier=<Identifier value='ev'>>>
            ]>>
        ]>
        """,
    ), (
        'iteration_var_in_obj',
        """
        for (var p in obj) {
          p = 1;
        }
        """,
        """
        <ES5Program ?children=[<ForIn item=<VarDecl identifier=<
          Identifier value='p'>, initializer=None>, iterable=<
            Identifier value='obj'>, statement=<
              Block ?children=[
              <ExprStatement expr=<Assign left=<Identifier value='p'>,
                op='=', right=<Number value='1'>>>
              ]>
        >]>
        """,
    ), (
        'iteration_do_while',
        """
        do {
          x += 1;
        } while (true);
        """,
        """
        <ES5Program ?children=[<DoWhile predicate=<Boolean value='true'>,
          statement=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>,
              op='+=', right=<Number value='1'>>>
          ]>>
        ]>
        """,
    ), (
        'while_loop',
        """
        while (false) {
          x = null;
        }
        """,
        """
        <ES5Program ?children=[
          <While predicate=<Boolean value='false'>,
            statement=<Block ?children=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='=', right=<Null value='null'>>>
            ]>
          >
        ]>
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
        """
        <ES5Program ?children=[
          <While predicate=<Boolean value='true'>, statement=<Block ?children=[
            <Continue identifier=None>,
            <ExprStatement expr=<Assign left=<Identifier value='s'>,
              op='=', right=<String value="'I am not reachable'">>>
          ]>>
        ]>
        """,
    ), (
        'while_loop_continue_label',
        """
        while (true) {
          continue label1;
          s = 'I am not reachable';
        }
        """,
        """
        <ES5Program ?children=[
          <While predicate=<Boolean value='true'>, statement=<Block ?children=[
            <Continue identifier=<Identifier value='label1'>>,
            <ExprStatement expr=<Assign left=<Identifier value='s'>,
              op='=', right=<String value="'I am not reachable'">>>
          ]>>
        ]>
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
        """
        <ES5Program ?children=[
          <While predicate=<Boolean value='true'>,
            statement=<Block ?children=[
              <Break identifier=None>,
              <ExprStatement expr=<Assign left=<Identifier value='s'>,
                op='=', right=<String value="'I am not reachable'">>>
            ]
          >>
        ]>
        """,
    ), (
        'while_loop_break_label',
        """
        while (true) {
          break label1;
          s = 'I am not reachable';
        }
        """,
        """
        <ES5Program ?children=[
          <While predicate=<Boolean value='true'>, statement=<Block ?children=[
            <Break identifier=<Identifier value='label1'>>,
            <ExprStatement expr=<Assign left=<Identifier value='s'>,
              op='=', right=<String value="'I am not reachable'">>>
          ]>>
        ]>
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
        """
        <ES5Program ?children=[<Block ?children=[<Return expr=None>]>]>
        """,
    ), (
        'return_1',
        """
        {
          return 1;
        }
        """,
        """
        <ES5Program ?children=[
          <Block ?children=[<Return expr=<Number value='1'>>]>]>
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
        """
        <ES5Program ?children=[
          <With expr=<Identifier value='x'>, statement=<Block ?children=[
            <VarStatement ?children=[
              <VarDecl identifier=<Identifier value='y'>, initializer=
                <BinOp left=<Identifier value='x'>, op='*', right=
                <Number value='2'>>>
            ]>
          ]>>
        ]>
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
        """
        <ES5Program ?children=[<Label identifier=<
          Identifier value='label'>, statement=<
            While predicate=<Boolean value='true'>,
            statement=<Block ?children=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='*=', right=<Number value='3'>>>
            ]>
        >>]>
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
        """
        <ES5Program ?children=[<
          Switch cases=[
            <Case elements=[], expr=<Number value='6'>>,
            <Case elements=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='=', right=<String value="'Weekend'">>>,
              <Break identifier=None>
            ], expr=<Number value='7'>>,
            <Case elements=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='=', right=<String value="'Monday'">>>,
              <Break identifier=None>
            ], expr=<Number value='1'>>
          ],
          default=<Default elements=[
            <Break identifier=None>
          ]>,
          expr=<Identifier value='day_of_week'>>
        ]>
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
        """
        <ES5Program ?children=[<Throw expr=<String value="'exc'">>]>
        """,
    ), (
        ################################
        # debugger statement
        ################################
        'debugger_statement',
        'debugger;',
        """
        <ES5Program ?children=[<Debugger value='debugger'>]>
        """,
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
        1 << 2;
        foo = 2 << 3;
        1 < 2;
        bar = 1 < 2;
        1 | 2;
        bar = 1 & 2;
        1 | 2 & 8;
        bar = 1 & 2 | 8;
        x ^ y;
        bar = x ^ y;
        x && y;
        bar = x && y;
        1,2;
        """,

        """
        <ES5Program ?children=[
          <ExprStatement expr=<BinOp left=<BinOp left=<Number value='5'>,
            op='+', right=<Number value='7'>>, op='-',
            right=<BinOp left=<Number value='20'>, op='*',
              right=<Number value='10'>>>>,
          <ExprStatement expr=<UnaryOp op='++', postfix=False, value=<
            Identifier value='x'>>>,
          <ExprStatement expr=<UnaryOp op='--', postfix=False, value=<
            Identifier value='x'>>>,
          <ExprStatement expr=<UnaryOp op='++', postfix=True, value=<
            Identifier value='x'>>>,
          <ExprStatement expr=<UnaryOp op='--', postfix=True, value=<
            Identifier value='x'>>>,
          <ExprStatement expr=<Assign left=<Identifier value='x'>, op='=',
            right=<Assign left=<Number value='17'>, op='/=',
              right=<Number value='3'>>>>,
          <ExprStatement expr=<Assign left=<Identifier value='s'>, op='=',
            right=<Conditional alternative=<BinOp left=<
              Regex value='/x:3;x<5;y</g'>, op='/', right=<
                Identifier value='i'>>,
              consequent=<Identifier value='z'>,
              predicate=<Identifier value='mot'>>>>,
          <ExprStatement expr=<BinOp left=<Number value='1'>, op='<<',
            right=<Number value='2'>>>,
          <ExprStatement expr=<Assign left=<Identifier value='foo'>,
            op='=', right=<BinOp left=<Number value='2'>, op='<<',
              right=<Number value='3'>>>>,
          <ExprStatement expr=<BinOp left=<Number value='1'>, op='<',
            right=<Number value='2'>>>,
          <ExprStatement expr=<Assign left=<Identifier value='bar'>, op='=',
            right=<BinOp left=<Number value='1'>, op='<',
              right=<Number value='2'>>>>,
          <ExprStatement expr=<BinOp left=<Number value='1'>, op='|',
            right=<Number value='2'>>>,
          <ExprStatement expr=<Assign left=<Identifier value='bar'>, op='=',
            right=<BinOp left=<Number value='1'>, op='&',
              right=<Number value='2'>>>>,
          <ExprStatement expr=<BinOp left=<Number value='1'>, op='|',
            right=<BinOp left=<Number value='2'>, op='&',
              right=<Number value='8'>>>>,
          <ExprStatement expr=<Assign left=<Identifier value='bar'>, op='=',
            right=<BinOp left=<BinOp left=<Number value='1'>, op='&',
              right=<Number value='2'>>, op='|', right=<Number value='8'>>>>,
          <ExprStatement expr=<BinOp left=<Identifier value='x'>, op='^',
            right=<Identifier value='y'>>>,
          <ExprStatement expr=<Assign left=<Identifier value='bar'>, op='=',
            right=<BinOp left=<Identifier value='x'>, op='^',
              right=<Identifier value='y'>>>>,
          <ExprStatement expr=<BinOp left=<Identifier value='x'>, op='&&',
            right=<Identifier value='y'>>>,
          <ExprStatement expr=<Assign left=<Identifier value='bar'>, op='=',
            right=<BinOp left=<Identifier value='x'>, op='&&',
              right=<Identifier value='y'>>>>,
          <ExprStatement expr=<Comma left=<Number value='1'>,
            right=<Number value='2'>>>
        ]>
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
        """
        <ES5Program ?children=[<Try catch=<
          Catch elements=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>,
              op='=', right=<Identifier value='exc'>>>
            ]>,
            identifier=<Identifier value='exc'>
          >,
          fin=None,
          statements=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>, op='=',
              right=<Number value='3'>>>
          ]>
        >]>
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
        """
        <ES5Program ?children=[<Try catch=None,
          fin=<Finally ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>, op='=',
              right=<Null value='null'>>>
            ], elements=<Block ?children=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='=', right=<Null value='null'>>>
              ]
            >
          >,
          statements=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>,
              op='=', right=<Number value='3'>>>
          ]>
        >]>
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
        """
        <ES5Program ?children=[<Try catch=<
          Catch elements=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>,
              op='=', right=<Identifier value='exc'>>>
            ]>, identifier=<Identifier value='exc'>>,
          fin=<Finally ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='y'>, op='=',
              right=<Null value='null'>>>
            ], elements=<Block ?children=[
              <ExprStatement expr=<Assign left=<Identifier value='y'>, op='=',
                right=<Null value='null'>>>
            ]>>,
          statements=<Block ?children=[
            <ExprStatement expr=<Assign left=<Identifier value='x'>, op='=',
              right=<Number value='5'>>>
          ]>
        >]>
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
        """
        <ES5Program ?children=[
          <FuncDecl elements=[
            <ExprStatement expr=<Assign left=<Identifier value='z'>, op='=',
              right=<Number value='10'>>>,
            <Return expr=<BinOp left=<BinOp left=<
              Identifier value='x'>, op='+', right=<
              Identifier value='y'>
            >, op='+', right=<Identifier value='z'>>>
          ], identifier=<Identifier value='foo'>, parameters=[
            <Identifier value='x'>, <Identifier value='y'>]>
        ]>
        """,
    ), (
        'function_without_arguments',
        """
        function foo() {
          return 10;
        }
        """,
        """
        <ES5Program ?children=[
          <FuncDecl elements=[<Return expr=<Number value='10'>>],
            identifier=<Identifier value='foo'>, parameters=[]>
        ]>
        """,
    ), (
        'var_function_without_arguments',
        """
        var a = function() {
          return 10;
        };
        """,
        """
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>,
              initializer=<FuncExpr elements=[
                <Return expr=<Number value='10'>>
              ],
              identifier=None, parameters=[]>
            >
          ]>
        ]>
        """,
    ), (
        # test 33
        'var_function_with_arguments',
        """
        var a = function foo(x, y) {
          return x + y;
        };
        """,
        """
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>,
              initializer=<FuncExpr elements=[
                <Return expr=<BinOp left=<Identifier value='x'>,
                  op='+', right=<Identifier value='y'>>>
              ], identifier=<Identifier value='foo'>, parameters=[
                <Identifier value='x'>, <Identifier value='y'>
              ]>
            >
          ]>]>
        """,
    ), (
        'var_function_named',
        """
        var x = function y() {
        };
        """,
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='x'>,
            initializer=<FuncExpr elements=[],
              identifier=<Identifier value='y'>, parameters=[]>>]>]>
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
        """
        <ES5Program ?children=[
          <FuncDecl elements=[
            <FuncDecl elements=[], identifier=<Identifier value='bar'>,
              parameters=[]>
            ], identifier=<Identifier value='foo'>, parameters=[]>
        ]>
        """,
    ), (
        # function call
        # test 36
        'function_call',
        """
        foo();
        var r = foo();
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<FunctionCall args=[], identifier=<
            Identifier value='foo'>>>,
          <VarStatement ?children=[<VarDecl identifier=<Identifier value='r'>,
            initializer=<FunctionCall args=[],
              identifier=<Identifier value='foo'>>>]>
        ]>
        """,
    ), (
        'function_call_argument',
        """
        foo(x, 7);
        var r = foo(x, 7);
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<FunctionCall args=[
            <Identifier value='x'>, <Number value='7'>
          ], identifier=<Identifier value='foo'>>>,
          <VarStatement ?children=[<VarDecl identifier=<Identifier value='r'>,
            initializer=<FunctionCall args=[<Identifier value='x'>,
              <Number value='7'>], identifier=<Identifier value='foo'>>>
          ]>
        ]>
        """,
    ), (
        'function_call_access_element',
        """
        foo()[10];
        var j = foo()[10];
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<BracketAccessor expr=<Number value='10'>,
            node=<FunctionCall args=[], identifier=<Identifier value='foo'>>>>,
          <VarStatement ?children=[<VarDecl identifier=<Identifier value='j'>,
            initializer=<BracketAccessor expr=<Number value='10'>,
              node=<FunctionCall args=[], identifier=<
                Identifier value='foo'>>>>
          ]>
        ]>
        """,
    ), (
        'function_call_access_attribute',
        """
        foo().foo;
        var bar = foo().foo;
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<DotAccessor identifier=<Identifier value='foo'>,
            node=<FunctionCall args=[], identifier=<Identifier value='foo'>>>>,
          <VarStatement ?children=[<VarDecl identifier=<
            Identifier value='bar'>, initializer=<DotAccessor identifier=<
              Identifier value='foo'>,
            node=<FunctionCall args=[],
              identifier=<Identifier value='foo'>>>>]>
        ]>
        """,
    ), (
        'new_keyword',
        """
        var foo = new Foo();
        """,
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='foo'>, initializer=<
            NewExpr args=[], identifier=<Identifier value='Foo'>>>
        ]>]>
        """,
    ), (
        # dot accessor
        'new_keyword_dot_accessor',
        'var bar = new Foo.Bar();',
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='bar'>, initializer=<
            NewExpr args=[], identifier=<DotAccessor identifier=<
              Identifier value='Bar'>, node=<Identifier value='Foo'>>>>
        ]>]>
        """,
    ), (
        # bracket accessor
        'new_keyword_bracket_accessor',
        'var bar = new Foo.Bar()[7];',
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='bar'>, initializer=<
            BracketAccessor expr=<Number value='7'>, node=<
              NewExpr args=[], identifier=<DotAccessor identifier=<
                Identifier value='Bar'>, node=<Identifier value='Foo'>>>>>
        ]>]>
        """,

    ), (
        # object literal
        'object_literal_literal_keys',
        """
        var obj = {
          foo: 10,
          bar: 20
        };
        """,
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='obj'>, initializer=<
            Object properties=[
              <Assign left=<Identifier value='foo'>, op=':', right=<
                Number value='10'>>,
              <Assign left=<Identifier value='bar'>, op=':', right=<
                Number value='20'>>
            ]
          >>
        ]>]>
        """,
    ), (
        'object_literal_numeric_keys',
        """
        var obj = {
          1: 'a',
          2: 'b'
        };
        """,
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='obj'>, initializer=<
            Object properties=[
              <Assign left=<Number value='1'>, op=':', right=<
                String value="'a'">>,
              <Assign left=<Number value='2'>, op=':', right=<
                String value="'b'">>
            ]
          >>
        ]>]>
        """,
    ), (
        'new_expr_lhs',
        """
        new T()
        new T().derp
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<NewExpr args=[], identifier=<
            Identifier value='T'>>>,
          <ExprStatement expr=<DotAccessor identifier=<
            Identifier value='derp'>, node=<
              NewExpr args=[], identifier=<Identifier value='T'>>>>
        ]>
        """
    ), (
        'new_new_expr',
        # var T = function(){ return function (){} }
        """
        new new T()
        var x = new new T()
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<NewExpr args=[], identifier=<NewExpr args=[],
            identifier=<Identifier value='T'>>>>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='x'>,
              initializer=<NewExpr args=[],
                identifier=<NewExpr args=[],
                  identifier=<Identifier value='T'>>>>
          ]>
        ]>
        """
    ), (
        'object_literal_string_keys',
        """
        var obj = {
          'a': 100,
          'b': 200
        };
        """,
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='obj'>, initializer=<
            Object properties=[
              <Assign left=<String value="'a'">, op=':', right=<
                Number value='100'>>,
              <Assign left=<String value="'b'">, op=':', right=<
                Number value='200'>>
            ]
          >>
        ]>]>
        """,
    ), (
        'object_literal_empty',
        """
        var obj = {
        };
        """,
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='obj'>,
            initializer=<Object properties=[]>>
        ]>]>
        """,

    ), (
        # delete
        'delete_keyword',
        """
        var obj = {foo: 1};
        delete obj.foo;
        """,
        """
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='obj'>, initializer=<
              Object properties=[
                <Assign left=<Identifier value='foo'>, op=':', right=<
                  Number value='1'>>
              ]>>
          ]>,
          <ExprStatement expr=<UnaryOp op='delete', postfix=False,
            value=<DotAccessor identifier=<Identifier value='foo'>,
              node=<Identifier value='obj'>>>>
        ]>
        """,
    ), (
        'void_keyword',
        """
        void 0;
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<UnaryOp op='void', postfix=False,
            value=<Number value='0'>>>
        ]>
        """,
    ), (
        # array
        'array_create_access',
        """
        var a = [1,2,3,4,5];
        var b = [1,];
        var c = [1,,];
        var res = a[3];
        """,
        """
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='a'>,
              initializer=<Array items=[
                <Number value='1'>, <Number value='2'>, <Number value='3'>,
                <Number value='4'>, <Number value='5'>]>>]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='b'>,
              initializer=<Array items=[<Number value='1'>]>>]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='c'>,
              initializer=<Array items=[
                <Number value='1'>, <Elision value=','>]>>]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier value='res'>,
              initializer=<BracketAccessor expr=<Number value='3'>,
                node=<Identifier value='a'>>>]>
        ]>
        """,
    ), (
        # elision
        'elision_1',
        'var a = [,,,];',
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='a'>,
            initializer=<Array items=[
              <Elision value=','>, <Elision value=','>, <Elision value=','>
            ]>>
          ]>
        ]>
        """,
    ), (
        'elision_2',
        'var a = [1,,,4];',
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='a'>,
            initializer=<Array items=[
              <Number value='1'>, <Elision value=','>, <Elision value=','>,
              <Number value='4'>
            ]>>
          ]>
        ]>
        """,
    ), (
        'elision_3',
        'var a = [1,,3,,5];',
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='a'>,
            initializer=<Array items=[
              <Number value='1'>, <Elision value=','>, <Number value='3'>,
              <Elision value=','>, <Number value='5'>
            ]>>
          ]>
        ]>
        """,
    ), (

        #######################################
        # Make sure parentheses are not removed
        #######################################

        # ... Expected an identifier and instead saw '/'
        'parentheses_not_removed',
        r'Expr.match[type].source + (/(?![^\[]*\])(?![^\(]*\))/.source);',

        r"""
        <ES5Program ?children=[<ExprStatement expr=<BinOp left=<
          DotAccessor identifier=<Identifier value='source'>, node=<
            BracketAccessor expr=<Identifier value='type'>, node=<
              DotAccessor identifier=<Identifier value='match'>,
              node=<Identifier value='Expr'>>>>,
          op='+', right=<DotAccessor identifier=<Identifier value='source'>,
            node=<Regex value='/(?![^\\[]*\\])(?![^\\(]*\\))/'>>>>]>
        """,
    ), (
        'comparison',
        '(options = arguments[i]) != null;',
        # test 54
        """
        <ES5Program ?children=[
          <ExprStatement expr=<
            BinOp left=<
              Assign left=<Identifier value='options'>, op='=',
                right=<BracketAccessor expr=<Identifier value='i'>,
                node=<Identifier value='arguments'>>
            >, op='!=', right=<Null value='null'>
          >>
        ]>
        """,
    ), (
        'regex_test',
        'return (/h\d/i).test(elem.nodeName);',
        r"""
        <ES5Program ?children=[<Return expr=<FunctionCall args=[
          <DotAccessor identifier=<Identifier value='nodeName'>,
            node=<Identifier value='elem'>>], identifier=<
              DotAccessor identifier=<Identifier value='test'>,
                node=<Regex value='/h\\d/i'>>>>]>
        """,

    ), (
        # https://github.com/rspivak/slimit/issues/42
        'slimit_issue_42',
        """
        e.b(d) ? (a = [c.f(j[1])], e.fn.attr.call(a, d, !0)) : a = [k.f(j[1])];
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<Conditional alternative=<Assign left=<
            Identifier value='a'>, op='=', right=<Array items=[
              <FunctionCall args=[<BracketAccessor expr=<Number value='1'>,
                node=<Identifier value='j'>>],
                identifier=<DotAccessor identifier=<Identifier value='f'>,
                node=<Identifier value='k'>>>
            ]>>, consequent=
              <Comma left=<Assign left=<Identifier value='a'>,
                op='=', right=<Array items=[
                  <FunctionCall args=[
                    <BracketAccessor expr=<Number value='1'>,
                      node=<Identifier value='j'>>
                    ], identifier=<DotAccessor identifier=<
                      Identifier value='f'>, node=<Identifier value='c'>>>
                  ]>
                >,
                right=<FunctionCall args=[
                  <Identifier value='a'>,
                  <Identifier value='d'>,
                  <UnaryOp op='!', postfix=False, value=<Number value='0'>>
                ],
                identifier=<DotAccessor identifier=<Identifier value='call'>,
                  node=<DotAccessor identifier=<Identifier value='attr'>,
                    node=<DotAccessor identifier=<Identifier value='fn'>,
                      node=<Identifier value='e'>
                    >
                  >>
                >
              >,
            predicate=<FunctionCall args=[
              <Identifier value='d'>
            ], identifier=<DotAccessor identifier=<Identifier value='b'>,
              node=<Identifier value='e'>
            >>
          >>
        ]>
        """,
    ), (
        'closure_scope',
        """
        (function() {
          x = 5;
        }());
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<FunctionCall args=[],
            identifier=<FuncExpr elements=[
              <ExprStatement expr=<Assign left=<Identifier value='x'>,
                op='=', right=<Number value='5'>>>
            ], identifier=None, parameters=[]>>>
        ]>
        """,
    ), (
        'return_statement_negation',
        'return !(match === true || elem.getAttribute("classid") !== match);',
        """
        <ES5Program ?children=[<Return expr=<
          UnaryOp op='!', postfix=False, value=<BinOp left=<BinOp left=<
            Identifier value='match'>,
            op='===', right=<Boolean value='true'>>, op='||', right=<
              BinOp left=<FunctionCall args=[<String value='"classid"'>],
                identifier=<DotAccessor identifier=<
                  Identifier value='getAttribute'
                >, node=<Identifier value='elem'>>>, op='!==',
              right=<Identifier value='match'>>>
        >>]>
        """,
    ), (
        # test 57
        'ternary_dot_accessor',
        'var el = (elem ? elem.ownerDocument || elem : 0).documentElement;',
        """
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='el'>,
            initializer=<DotAccessor identifier=<
              Identifier value='documentElement'>,
              node=<Conditional alternative=<Number value='0'>,
              consequent=<BinOp left=<DotAccessor identifier=<
                Identifier value='ownerDocument'>,
                node=<Identifier value='elem'>
              >,
              op='||', right=<Identifier value='elem'>>,
            predicate=<Identifier value='elem'>>>
          >
        ]>]>
        """,
    ), (
        # typeof
        'typeof',
        'typeof second.length === "number";',
        """
        <ES5Program ?children=[
          <ExprStatement expr=<BinOp left=<UnaryOp op='typeof',
            postfix=False, value=<DotAccessor identifier=
              <Identifier value='length'>, node=<Identifier value='second'>>>,
            op='===', right=<String value='"number"'
          >>>
        ]>
        """,
    ), (
        'instanceof',
        'x instanceof y',
        """
        <ES5Program ?children=[
          <ExprStatement expr=<BinOp left=<Identifier value='x'>,
            op='instanceof', right=<Identifier value='y'>>>
        ]>
        """,
    ), (
        # membership
        'membership_in',
        """
        1 in s;
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<BinOp left=<Number value='1'>, op='in',
            right=<Identifier value='s'>>>
        ]>
        """,
    ), (
        # function call in FOR init
        'function_call_in_for_init',
        """
        for (o(); i < 3; i++) {

        }
        """,

        """
        <ES5Program ?children=[
          <For cond=<BinOp left=<Identifier value='i'>, op='<',
            right=<Number value='3'>>, count=<UnaryOp op='++', postfix=True,
            value=<Identifier value='i'>>, init=<
              FunctionCall args=[], identifier=<Identifier value='o'>>,
            statement=<Block >>
        ]>
        """,
    ), (
        'for_loop_chained_noin',
        """
        for (o < (p < q);;);
        for (o == (p == q);;);
        for (o ^ (p ^ q);;);
        for (o | (p | q);;);
        for (o & (p & q);;);
        for (a ? (b ? c : d) : false;;);
        for (var x;;);
        """,
        """
        <ES5Program ?children=[
          <For cond=None, count=None, init=<BinOp left=<Identifier value='o'>,
              op='<', right=<BinOp left=<Identifier value='p'>, op='<',
            right=<Identifier value='q'>>>,
            statement=<EmptyStatement value=';'>>,
          <For cond=None, count=None, init=<BinOp left=<Identifier value='o'>,
              op='==', right=<BinOp left=<Identifier value='p'>, op='==',
            right=<Identifier value='q'>>>,
            statement=<EmptyStatement value=';'>>,
          <For cond=None, count=None, init=<BinOp left=<Identifier value='o'>,
              op='^', right=<BinOp left=<Identifier value='p'>, op='^',
            right=<Identifier value='q'>>>,
            statement=<EmptyStatement value=';'>>,
          <For cond=None, count=None, init=<BinOp left=<Identifier value='o'>,
              op='|', right=<BinOp left=<Identifier value='p'>, op='|',
            right=<Identifier value='q'>>>,
            statement=<EmptyStatement value=';'>>,
          <For cond=None, count=None, init=<BinOp left=<Identifier value='o'>,
              op='&', right=<BinOp left=<Identifier value='p'>, op='&',
            right=<Identifier value='q'>>>,
            statement=<EmptyStatement value=';'>>,
          <For cond=None, count=None, init=<Conditional alternative=<
              Boolean value='false'>, consequent=<Conditional alternative=<
                Identifier value='d'>, consequent=<Identifier value='c'>,
                  predicate=<Identifier value='b'>>,
                predicate=<Identifier value='a'>>,
            statement=<EmptyStatement value=';'>>,
          <For cond=None, count=None, init=<VarStatement ?children=[
              <VarDecl identifier=<Identifier value='x'>, initializer=None>]>,
            statement=<EmptyStatement value=';'>>
        ]>
        """,

    ), (
        'for_initializer_noin',
        """
        for (var x = foo() in (bah())) {};
        """,
        """
        <ES5Program ?children=[<ForIn item=<VarDecl identifier=<
          Identifier value='x'>, initializer=<FunctionCall args=[],
            identifier=<Identifier value='foo'>>>, iterable=<
              FunctionCall args=[], identifier=<
                Identifier value='bah'>>,
            statement=<Block >>,
          <EmptyStatement value=';'>
        ]>
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
        """
        <ES5Program ?children=[<
          ExprStatement expr=<Assign left=<DotAccessor identifier=<
            Identifier value='prototype'>, node=<
              Identifier value='Name'>>,
            op='=', right=<Object properties=[
              <GetPropAssign elements=[
                <Return expr=<BinOp left=<BinOp left=<DotAccessor identifier=<
                  Identifier value='first'>, node=<This >>,
                  op='+', right=<String value='" "'>>,
                  op='+', right=<DotAccessor identifier=<
                    Identifier value='last'>, node=<This >>>>
                ], prop_name=<Identifier value='fullName'>>,
                <SetPropAssign elements=[
                  <VarStatement ?children=[
                    <VarDecl identifier=<Identifier value='names'>,
                      initializer=<FunctionCall args=[<String value='" "'>],
                        identifier=<
                          DotAccessor identifier=<Identifier value='split'>,
                          node=<Identifier value='name'>>>>
                  ]>,
                  <ExprStatement expr=<
                    Assign left=<DotAccessor identifier=<
                      Identifier value='first'>, node=<This >
                    >, op='=', right=<BracketAccessor expr=<Number value='0'>,
                      node=<Identifier value='names'>>>>,
                  <ExprStatement expr=<Assign left=<DotAccessor identifier=<
                    Identifier value='last'>, node=<This >>,
                    op='=', right=<BracketAccessor expr=<Number value='1'>,
                      node=<Identifier value='names'>>>>
                  ], parameters=[<Identifier value='name'>],
                  prop_name=<Identifier value='fullName'>>
            ]>
          >
        >]>
        """,
    ), (
        'dot_accessor_on_integer',
        """
        (0).toString();
        """,
        """
        <ES5Program ?children=[
          <ExprStatement expr=<FunctionCall args=[], identifier=<
            DotAccessor identifier=<Identifier value='toString'>,
            node=<Number value='0'>>>>
        ]>
        """,
    ), (
        'dot_reserved_word',
        """
        e.case;
        """,
        """
        <ES5Program ?children=[<ExprStatement expr=<
          DotAccessor identifier=<Identifier value='case'>,
            node=<Identifier value='e'>>>
        ]>
        """
    ), (
        'dot_reserved_word_nobf',
        """
        for (x = e.case;;);
        """,
        """
        <ES5Program ?children=[
          <For cond=None, count=None, init=<Assign left=<Identifier value='x'>,
            op='=', right=<DotAccessor identifier=<Identifier value='case'>,
              node=<Identifier value='e'>>>,
                statement=<EmptyStatement value=';'>>
        ]>
        """
    ), (
        'octal_slimit_issue_70',
        r"var x = '\071[90m%s';",
        r"""
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='x'>, initializer=<
            String value="'\\071[90m%s'">>
        ]>]>
        """
    ), (
        'special_array_char_slimit_issue_82',
        r"var x = ['a','\n'];",
        r"""
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='x'>,
            initializer=<Array items=[
              <String value="'a'">,
              <String value="'\\n'">
            ]>
          >
        ]>]>
        """
    ), (
        'special_string_slimit_issue_82',
        r"var x = '\n';",
        r"""
        <ES5Program ?children=[<VarStatement ?children=[
          <VarDecl identifier=<Identifier value='x'>,
            initializer=<String value="'\\n'">>
        ]>]>
        """
    ), (
        'for_in_without_braces',
        "for (index in [1,2,3]) index",
        """
        <ES5Program ?children=[
          <ForIn item=<Identifier value='index'>, iterable=<Array items=[
            <Number value='1'>, <Number value='2'>, <Number value='3'>
          ]>, statement=<ExprStatement expr=<Identifier value='index'>>>
        ]>
        """
    ), (
        'for_loop_into_regex_slimit_issue_54',
        # "for (index in [1,2,3]) /^salign$/i.test('salign')",
        "for (index in [1,2,3]) /^salign$/",
        """
        <ES5Program ?children=[
          <ForIn item=<Identifier value='index'>, iterable=<Array items=[
            <Number value='1'>, <Number value='2'>, <Number value='3'>
          ]>, statement=<ExprStatement expr=<Regex value='/^salign$/'>>>
        ]>
        """
    )])
)


# ASI - Automatic Semicolon Insertion

def regenerate(value):
    parser = Parser()
    return pretty_print(parser.parse(value))


ParserToECMAASITestCase = build_equality_testcase(
    'ParserToECMAASITestCase', regenerate, ((
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
        [true, false, null, undefined]
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
          return e.default
        }
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
          x / 0
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
    ), (
        'regex',
        r"""
        r = /foo/
        q = /default/g
        """,
        r"""
        r = /foo/;
        q = /default/g;
        """
    ), (
        'regex_section_7',
        r"""
        a = b
        /hi/g.exec(c).map(d);
        """,
        r"""
        a = b / hi / g.exec(c).map(d);
        """
    ), (
        'new_expr',
        r"""
        var T = function() {}
        a = new T()
        """,
        r"""
        var T = function() {

        };
        a = new T();
        """
    ), (
        'bracket_accessor',
        """
        foo = [1, 2, 3][1]
        """,
        """
        foo = [1,2,3][1];
        """
    ), (
        'get_prop_assignment',
        """
        foo = {get bar() {return 1}}
        """,
        """
        foo = {
          get bar() {
            return 1;
          }
        };
        """
    ), (
        'set_prop_assignment',
        """
        foo = {set bar(x) {this.x = x}}
        """,
        """
        foo = {
          set bar(x) {
            this.x = x;
          }
        };
        """
    ), (
        'conditional_standard',
        """
        x ? y : z
        x ? y : z
        """,
        """
        x ? y : z;
        x ? y : z;
        """
    ), (
        'conditional_standard_overflowed',
        """
        x ?
        y :
        z
        """,
        """
        x ? y : z;
        """
    ), (
        'bare_strings_issue_62',
        u"""
        \xef
        'use strict';
        'use strict';
        'use strict';
        """,
        u"""
        \xef;
        'use strict';
        'use strict';
        'use strict';
        """,
    )])
)


ECMASyntaxErrorsTestCase = build_exception_testcase(
    'ECMASyntaxErrorsTestCase', parse_to_repr, ((
        label,
        textwrap.dedent(argument).strip(),
    ) for label, argument in [(
        'interger_unwrapped_raw_dot_accessor',
        '0.toString();'
    ), (
        'unterminated_comment',  # looks like regex
        's = /****/;'
    ), (
        # expression is not optional in throw statement
        # ASI at lexer level should insert ';' after throw
        'throw_error_asi',
        """
        throw
          'exc';
        """
    )]), ECMASyntaxError
)


ECMARegexSyntaxErrorsTestCase = build_exception_testcase(
    'ECMARegexSyntaxErrorsTestCase', parse_to_repr, ((
        label,
        textwrap.dedent(argument).strip(),
    ) for label, argument in [(
        'unmatched_brackets',
        'var x = /][/;'
    ), (
        'unmatched_backslash',
        r'var x = /\/;'
    )]), ECMARegexSyntaxError
)
