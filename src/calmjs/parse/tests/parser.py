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

from __future__ import unicode_literals

import textwrap

from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.exceptions import ECMARegexSyntaxError
from calmjs.parse.walkers import ReprWalker

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase


class ParserCaseMixin(object):

    def test_line_terminator_at_the_end_of_file(self):
        self.parse('var $_ = function(x){}(window);\n')

    def test_wrong_type(self):
        with self.assertRaises(TypeError) as e:
            self.parse(b'var bytes = "banned"')
        # exact message depends on Python version
        self.assertIn('argument expected, got', e.exception.args[0])

    def test_bad_char_error(self):
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse('var\x01 blagh = 1;')
        self.assertEqual(
            e.exception.args[0],
            "Illegal character '\\x01' at 1:4 after 'var' at 1:1"
        )

    def test_bug_no_semicolon_at_the_end_of_block_plus_newline_at_eof(self):
        # https://github.com/rspivak/slimit/issues/3
        text = textwrap.dedent("""
        function add(x, y) {
          return x + y;
        }
        """).strip()
        tree = self.parse(text)
        self.assertTrue(bool(tree.children()))

    def test_function_expression_is_part_of_member_expr_nobf(self):
        # https://github.com/rspivak/slimit/issues/22
        # The problem happened to be that function_expr was not
        # part of member_expr_nobf rule
        text = 'window.done_already || function () { return "slimit!" ; }();'
        self.assertTrue(bool(self.parse(text).children()))

    # https://github.com/rspivak/slimit/issues/29
    def test_that_parsing_eventually_stops(self):
        text = textwrap.dedent("""
        var a;
        , b;
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            "Unexpected ',' at 2:1 after ';' at 1:6")

    def test_bare_start(self):
        text = textwrap.dedent("""
        <
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            "Unexpected end of input after '<' at 1:1")

    def test_previous_token(self):
        text = textwrap.dedent("""
        throw;
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            "Unexpected ';' at 1:6 after 'throw' at 1:1")

    def test_skip_var_autosemi_in_function(self):
        text = textwrap.dedent("""
        (function() { var })()
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected '}' at 1:19 after 'var' at 1:15", str(e.exception),
        )

    def test_skip_throw_autosemi_in_function(self):
        text = textwrap.dedent("""
        (function() { throw })()
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected '}' at 1:21 after 'throw' at 1:15", str(e.exception),
        )

    def test_report_var_real_tokens(self):
        text = textwrap.dedent("""
        var;
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected ';' at 1:4 after 'var' at 1:1", str(e.exception),
        )

    def test_report_do_real_tokens(self):
        text = textwrap.dedent("""
        do;
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected end of input after ';' at 1:3", str(e.exception),
        )

    def test_skip_do_auto_tokens(self):
        text = textwrap.dedent("""
        do
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected end of input after 'do' at 1:1", str(e.exception),
        )

    def test_skip_if_auto_tokens(self):
        text = textwrap.dedent("""
        if
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected end of input after 'if' at 1:1", str(e.exception),
        )

    def test_skip_var_auto_tokens(self):
        text = textwrap.dedent("""
        var
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            "Unexpected end of input after 'var' at 1:1", str(e.exception),
        )

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
        self.assertTrue(bool(self.parse(text).children()))

    # 7.9.2
    def test_asi_empty_if_parse_fail(self):
        text = "if (true)"
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            "Unexpected end of input after ')' at 1:9")

    def test_asi_empty_if_parse_fail_inside_block(self):
        # https://github.com/rspivak/slimit/issues/101
        text = textwrap.dedent("""
        function foo(args) {
            if (true)
        }
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            r"Unexpected '}' at 3:1 after ')' at 2:13")

    def test_asi_for_truncated_fail(self):
        text = textwrap.dedent("""
        for (a; b
        )
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            r"Unexpected ')' at 2:1 after 'b' at 1:9")

    def test_asi_for_bare_fail(self):
        text = textwrap.dedent("""
        for (a; b; c)
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            "Unexpected end of input after ')' at 1:13")

    def test_asi_omitted_if_else_fail(self):
        text = textwrap.dedent("""
        if (a > b)
        else c = d
        """).strip()
        with self.assertRaises(ECMASyntaxError) as e:
            self.parse(text)
        self.assertEqual(
            str(e.exception),
            r"Unexpected 'else' at 2:1 after ')' at 1:10")


repr_walker = ReprWalker()


def singleline(s):
    def clean(f):
        r = f.strip()
        return r + ' ' if r[-1:] == ',' else r
    return ''.join(clean(t) for t in textwrap.dedent(s).splitlines())


def format_repr_program_type(label, repr_output, program_type):
    result = singleline(repr_output)
    if not result.startswith('<Program'):
        raise ValueError(
            "repr test result for '%s' did not start with generic '<Program', "
            "got: %s" % (label, repr_output)
        )
    return result.replace('<Program', '<' + program_type)


def build_node_repr_test_cases(clsname, parse, program_type):

    def parse_to_repr(value):
        return repr_walker.walk(parse(value), pos=True)

    return build_equality_testcase(clsname, parse_to_repr, ((
        label,
        textwrap.dedent(argument).strip(),
        format_repr_program_type(label, result, program_type),
    ) for label, argument, result in [(
        'block',
        """
        {
          var a = 5;
        }
        """,
        """
        <Program @1:1 ?children=[
          <Block @1:1 ?children=[<VarStatement @2:3 ?children=[
            <VarDecl @2:7 identifier=<Identifier @2:7 value='a'>,
              initializer=<Number @2:11 value='5'>>
          ]>]>
        ]>
        """,
    ), (
        'block_empty',
        """
        {}
        """,
        """
        <Program @1:1 ?children=[
          <Block @1:1 >
        ]>
        """,
    ), (
        'block_empty_with_1_after',
        """
        {}1
        """,
        """
        <Program @1:1 ?children=[
          <Block @1:1 >,
          <ExprStatement @1:3 expr=<Number @1:3 value='1'>>
        ]>
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
        <Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
              initializer=None>
          ]>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='b'>,
              initializer=None>
          ]>,
          <VarStatement @3:1 ?children=[
            <VarDecl @3:5 identifier=<Identifier @3:5 value='a'>,
              initializer=None>,
            <VarDecl @3:8 identifier=<Identifier @3:8 value='b'>,
              initializer=<Number @3:12 value='3'>>
          ]>,
          <VarStatement @4:1 ?children=[
            <VarDecl @4:5 identifier=<Identifier @4:5 value='a'>,
              initializer=<Number @4:9 value='1'>>,
            <VarDecl @4:12 identifier=<Identifier @4:12 value='b'>,
              initializer=None>
          ]>,
          <VarStatement @5:1 ?children=[
            <VarDecl @5:5 identifier=<Identifier @5:5 value='a'>,
              initializer=<Number @5:9 value='5'>>,
            <VarDecl @5:12 identifier=<Identifier @5:12 value='b'>,
              initializer=<Number @5:16 value='7'>>
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
        <Program @1:1 ?children=[
          <EmptyStatement @1:1 value=';'>,
          <EmptyStatement @2:1 value=';'>,
          <EmptyStatement @3:1 value=';'>
        ]>
        """,
    ), (
        'if_statement_inline',
        'if (true) var x = 100;',
        """
        <Program @1:1 ?children=[<If @1:1 alternative=None,
          consequent=<VarStatement @1:11 ?children=[
            <VarDecl @1:15 identifier=<Identifier @1:15 value='x'>,
              initializer=<Number @1:19 value='100'>>
          ]>, predicate=<Boolean @1:5 value='true'>>
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
        <Program @1:1 ?children=[<If @1:1 alternative=None,
          consequent=<Block @1:11 ?children=[
            <VarStatement @2:3 ?children=[
              <VarDecl @2:7 identifier=<Identifier @2:7 value='x'>,
                initializer=<Number @2:11 value='100'>>
            ]>,
            <VarStatement @3:3 ?children=[
              <VarDecl @3:7 identifier=<Identifier @3:7 value='y'>,
                initializer=<Number @3:11 value='200'>>
            ]>
          ]>,
          predicate=<Boolean @1:5 value='true'>>
        ]>
        """,
    ), (
        'if_else_inline',
        'if (true) if (true) var x = 100; else var y = 200;',
        """
        <Program @1:1 ?children=[
          <If @1:1 alternative=None,
            consequent=<If @1:11 alternative=<VarStatement @1:39 ?children=[
              <VarDecl @1:43 identifier=<Identifier @1:43 value='y'>,
                initializer=<Number @1:47 value='200'>>
            ]>,
            consequent=<VarStatement @1:21 ?children=[
              <VarDecl @1:25 identifier=<Identifier @1:25 value='x'>,
                initializer=<Number @1:29 value='100'>>
            ]>, predicate=<Boolean @1:15 value='true'>>,
            predicate=<Boolean @1:5 value='true'>>
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
        <Program @1:1 ?children=[
          <If @1:1 alternative=<Block @3:8 ?children=[
            <VarStatement @4:3 ?children=[
              <VarDecl @4:7 identifier=<Identifier @4:7 value='y'>,
                initializer=<Number @4:11 value='200'>>
              ]>
            ]>,
            consequent=<Block @1:11 ?children=[
              <VarStatement @2:3 ?children=[
                <VarDecl @2:7 identifier=<Identifier @2:7 value='x'>,
                  initializer=<Number @2:11 value='100'>>
                ]>
              ]>,
            predicate=<Boolean @1:5 value='true'>>
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
        <Program @1:1 ?children=[
          <For @1:1 cond=<ExprStatement @1:17 expr=<BinOp @1:19 left=<
                Identifier @1:17 value='i'>,
              op='<',
              right=<Number @1:21 value='10'>>>,
            count=<PostfixExpr @1:26 op='++', value=<
              Identifier @1:25 value='i'>>,
            init=<VarStatement @1:6 ?children=[
                <VarDecl @1:10 identifier=<Identifier @1:10 value='i'>,
                  initializer=<Number @1:14 value='0'>>
              ]>,
            statement=<Block @1:30 ?children=[
              <ExprStatement @2:3 expr=<Assign @2:5 left=<
                Identifier @2:3 value='x'>, op='=', right=<
                  BinOp @2:10 left=<Number @2:7 value='10'>, op='*', right=<
                    Identifier @2:12 value='i'>>>>
            ]>>
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
        <Program @1:1 ?children=[<For @1:1 cond=<ExprStatement @1:21 expr=<
          BinOp @1:27 left=<
            BinOp @1:23 left=<Identifier @1:21 value='i'>, op='<', right=<
                Identifier @1:25 value='j'>>,
              op='&&', right=<BinOp @1:32 left=<Identifier @1:30 value='j'>,
                op='<', right=<Number @1:34 value='15'>>>>,
          count=<Comma @1:41 left=<PostfixExpr @1:39 op='++',
              value=<Identifier @1:38 value='i'>>,
            right=<PostfixExpr @1:44 op='++', value=<
              Identifier @1:43 value='j'>>>,
          init=<ExprStatement @1:6 expr=<
            Comma @1:11 left=<Assign @1:8 left=<
                Identifier @1:6 value='i'>,
              op='=', right=<Number @1:10 value='0'>>, right=<
                  Assign @1:15 left=<Identifier @1:13 value='j'>, op='=',
                right=<Number @1:17 value='10'>>>>,
          statement=<Block @1:48 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='x'>, op='=', right=<
                BinOp @2:9 left=<Identifier @2:7 value='i'>, op='*',
                  right=<Identifier @2:11 value='j'>>>>
          ]
        >>]>
        """,

    ), (
        'iteration_in',
        """
        for (p in obj) {

        }
        """,
        """
        <Program @1:1 ?children=[
          <ForIn @1:1 item=<Identifier @1:6 value='p'>,
            iterable=<Identifier @1:11 value='obj'>, statement=<Block @1:16 >>
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
        <Program @1:1 ?children=[<For @1:1 cond=
          <ExprStatement @1:21 expr=<BinOp @1:23 left=<
            Identifier @1:21 value='d'>, op='<', right=<
            Identifier @1:25 value='b'>>>,
          count=None,
          init=<ExprStatement @1:6 expr=<BinOp @1:8 left=<
            Identifier @1:6 value='Q'>,
              op='||', right=<GroupingOp @1:11 expr=<Assign @1:14 left=
                <Identifier @1:12 value='Q'>,
                op='=', right=<Array @1:16 items=[]>
            >>>>,
          statement=<Block @1:30 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='d'>, op='=',
              right=<Number @2:7 value='1'>>>
          ]
        >>]>
        """,
    ), (
        'iteration_ternary_initializer',
        """
        for (2 >> (foo ? 32 : 43) && 54; 21; ) {
          a = c;
        }
        """,
        """
        <Program @1:1 ?children=[<For @1:1 cond=
          <ExprStatement @1:34 expr=<Number @1:34 value='21'>>,
          count=None,
          init=<ExprStatement @1:6 expr=<
            BinOp @1:27 left=<BinOp @1:8 left=<
              Number @1:6 value='2'>, op='>>', right=
                <GroupingOp @1:11 expr=
                  <Conditional @1:16 alternative=<Number @1:23 value='43'>,
                    consequent=<Number @1:18 value='32'>,
                    predicate=<Identifier @1:12 value='foo'>>
              >>, op='&&', right=<Number @1:30 value='54'>>>,
          statement=<
            Block @1:40 ?children=[
              <ExprStatement @2:3 expr=<Assign @2:5 left=<
                Identifier @2:3 value='a'>, op='=', right=<
                  Identifier @2:7 value='c'>>>
            ]
          >
        >]>
        """,
    ), (
        'iteration_regex_initialiser',
        """
        for (/^.+/g; cond(); ++z) {
          ev();
        }
        """,
        """
        <Program @1:1 ?children=[
          <For @1:1 cond=<ExprStatement @1:14 expr=<FunctionCall @1:14 args=<
              Arguments @1:18 items=[]>,
              identifier=<Identifier @1:14 value='cond'>>>,
            count=<UnaryExpr @1:22 op='++',
              value=<Identifier @1:24 value='z'>>,
            init=<ExprStatement @1:6 expr=<Regex @1:6 value='/^.+/g'>>,
            statement=<Block @1:27 ?children=[
              <ExprStatement @2:3 expr=<FunctionCall @2:3 args=<
                Arguments @2:5 items=[]>,
                identifier=<Identifier @2:3 value='ev'>>>
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
        <Program @1:1 ?children=[<ForIn @1:1 item=<
          VarDeclNoIn @1:6 identifier=<Identifier @1:10 value='p'>,
            initializer=None>, iterable=<Identifier @1:15 value='obj'>,
          statement=<Block @1:20 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='p'>, op='=', right=<
                Number @2:7 value='1'>>>
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
        <Program @1:1 ?children=[<DoWhile @1:1 predicate=<
            Boolean @3:10 value='true'>,
          statement=<Block @1:4 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='x'>,
              op='+=', right=<Number @2:8 value='1'>>>
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
        <Program @1:1 ?children=[
          <While @1:1 predicate=<Boolean @1:8 value='false'>,
            statement=<Block @1:15 ?children=[
              <ExprStatement @2:3 expr=<Assign @2:5 left=
                <Identifier @2:3 value='x'>,
                op='=', right=<Null @2:7 value='null'>>>
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
        <Program @1:1 ?children=[
          <While @1:1 predicate=<Boolean @1:8 value='true'>,
            statement=<Block @1:14 ?children=[
              <Continue @2:3 identifier=None>,
              <ExprStatement @3:3 expr=<Assign @3:5 left=
                <Identifier @3:3 value='s'>, op='=',
                right=<String @3:7 value="'I am not reachable'">>>
            ]>
          >
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
        <Program @1:1 ?children=[
          <While @1:1 predicate=<Boolean @1:8 value='true'>,
            statement=<Block @1:14 ?children=[
              <Continue @2:3 identifier=<Identifier @2:12 value='label1'>>,
              <ExprStatement @3:3 expr=<Assign @3:5 left=
                <Identifier @3:3 value='s'>, op='=',
                right=<String @3:7 value="'I am not reachable'">>>
            ]>
          >
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
        <Program @1:1 ?children=[
          <While @1:1 predicate=<Boolean @1:8 value='true'>,
            statement=<Block @1:14 ?children=[
              <Break @2:3 identifier=None>,
              <ExprStatement @3:3 expr=<Assign @3:5 left=
                <Identifier @3:3 value='s'>, op='=',
                right=<String @3:7 value="'I am not reachable'">>>
            ]>
          >
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
        <Program @1:1 ?children=[
          <While @1:1 predicate=<Boolean @1:8 value='true'>,
            statement=<Block @1:14 ?children=[
              <Break @2:3 identifier=<Identifier @2:9 value='label1'>>,
              <ExprStatement @3:3 expr=<Assign @3:5 left=
                <Identifier @3:3 value='s'>, op='=',
                right=<String @3:7 value="'I am not reachable'">>>
            ]>
          >
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
        <Program @1:1 ?children=[<Block @1:1 ?children=[
          <Return @2:3 expr=None>]>]>
        """,
    ), (
        'return_1',
        """
        {
          return 1;
        }
        """,
        """
        <Program @1:1 ?children=[<Block @1:1 ?children=[
          <Return @2:3 expr=<Number @2:10 value='1'>>]>]>
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
        <Program @1:1 ?children=[
          <With @1:1 expr=<Identifier @1:7 value='x'>,
            statement=<Block @1:10 ?children=[
              <VarStatement @2:3 ?children=[
                <VarDecl @2:7 identifier=<Identifier @2:7 value='y'>,
                  initializer=<BinOp @2:13 left=<Identifier @2:11 value='x'>,
                    op='*', right=<Number @2:15 value='2'>>>
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
        <Program @1:1 ?children=[<Label @1:6 identifier=<
          Identifier @1:1 value='label'>, statement=<
            While @1:8 predicate=<Boolean @1:15 value='true'>,
            statement=<Block @1:21 ?children=[
              <ExprStatement @2:3 expr=<Assign @2:5 left=<
                Identifier @2:3 value='x'>, op='*=', right=<
                  Number @2:8 value='3'>>>
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
        <Program @1:1 ?children=[
          <Switch @1:1 case_block=<CaseBlock @1:22 ?children=[
            <Case @2:3 elements=[], expr=<Number @2:8 value='6'>>,
            <Case @3:3 elements=[
              <ExprStatement @4:5 expr=<Assign @4:7 left=<
                Identifier @4:5 value='x'>, op='=', right=<
                  String @4:9 value="'Weekend'">>>,
              <Break @5:5 identifier=None>
            ], expr=<Number @3:8 value='7'>>,
            <Case @6:3 elements=[
              <ExprStatement @7:5 expr=<Assign @7:7 left=<
                Identifier @7:5 value='x'>, op='=', right=<
                  String @7:9 value="'Monday'">>>,
              <Break @8:5 identifier=None>
            ], expr=<Number @6:8 value='1'>>,
            <Default @9:3 elements=[
              <Break @10:5 identifier=None>
            ]>
          ]>,
          expr=<Identifier @1:9 value='day_of_week'>>
        ]>
        """,

    ), (
        'switch_statement_case_default_case',
        """
        switch (result) {
          case 'good':
            do_good();
          case 'pass':
            do_pass();
            break;
          default:
            log_unexpected_result();
          case 'error':
            handle_error();
        }
        """,
        """
        <Program @1:1 ?children=[
          <Switch @1:1 case_block=<CaseBlock @1:17 ?children=[
            <Case @2:3 elements=[
                <ExprStatement @3:5 expr=<FunctionCall @3:5 args=
                  <Arguments @3:12 items=[]>,
                  identifier=<Identifier @3:5 value='do_good'>>>
            ], expr=<String @2:8 value="'good'">>,
            <Case @4:3 elements=[
              <ExprStatement @5:5 expr=<FunctionCall @5:5 args=
                <Arguments @5:12 items=[]>,
                identifier=<Identifier @5:5 value='do_pass'>>>,
              <Break @6:5 identifier=None>
            ], expr=<String @4:8 value="'pass'">>,
            <Default @7:3 elements=[
              <ExprStatement @8:5 expr=<FunctionCall @8:5 args=
                <Arguments @8:26 items=[]>,
                identifier=<Identifier @8:5 value='log_unexpected_result'>>>
            ]>,
            <Case @9:3 elements=[
              <ExprStatement @10:5 expr=<FunctionCall @10:5 args=
                <Arguments @10:17 items=[]>,
                identifier=<Identifier @10:5 value='handle_error'>>>
            ], expr=<String @9:8 value="'error'">>
          ]>, expr=<Identifier @1:9 value='result'>>
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
        <Program @1:1 ?children=[
          <Throw @1:1 expr=<String @1:7 value="'exc'">>
        ]>
        """,
    ), (
        ################################
        # debugger statement
        ################################
        'debugger_statement',
        'debugger;',
        """
        <Program @1:1 ?children=[<Debugger @1:1 value='debugger'>]>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:7 left=<BinOp @1:3 left=<
            Number @1:1 value='5'>, op='+', right=<Number @1:5 value='7'>>,
              op='-', right=<BinOp @1:12 left=<Number @1:9 value='20'>, op='*',
                right=<Number @1:14 value='10'>>>>,
          <ExprStatement @2:1 expr=<UnaryExpr @2:1 op='++',
            value=<Identifier @2:3 value='x'>>>,
          <ExprStatement @3:1 expr=<UnaryExpr @3:1 op='--',
            value=<Identifier @3:3 value='x'>>>,
          <ExprStatement @4:1 expr=<PostfixExpr @4:2 op='++',
            value=<Identifier @4:1 value='x'>>>,
          <ExprStatement @5:1 expr=<PostfixExpr @5:2 op='--',
            value=<Identifier @5:1 value='x'>>>,
          <ExprStatement @6:1 expr=<Assign @6:3 left=<
            Identifier @6:1 value='x'>, op='=',
            right=<Assign @6:8 left=<Number @6:5 value='17'>, op='/=',
              right=<Number @6:11 value='3'>>>>,
          <ExprStatement @7:1 expr=<Assign @7:3 left=<
            Identifier @7:1 value='s'>, op='=',
            right=<Conditional @7:9 alternative=<
              BinOp @7:29 left=<Regex @7:15 value='/x:3;x<5;y</g'>, op='/',
              right=<Identifier @7:31 value='i'>>,
              consequent=<Identifier @7:11 value='z'>,
              predicate=<Identifier @7:5 value='mot'>>>>,
          <ExprStatement @8:1 expr=<BinOp @8:3 left=<Number @8:1 value='1'>,
            op='<<', right=<Number @8:6 value='2'>>>,
          <ExprStatement @9:1 expr=<Assign @9:5 left=<
            Identifier @9:1 value='foo'>, op='=', right=<BinOp @9:9 left=<
              Number @9:7 value='2'>, op='<<', right=<
                Number @9:12 value='3'>>>>,
          <ExprStatement @10:1 expr=<BinOp @10:3 left=<Number @10:1 value='1'>,
            op='<', right=<Number @10:5 value='2'>>>,
          <ExprStatement @11:1 expr=<Assign @11:5 left=<
            Identifier @11:1 value='bar'>, op='=', right=<BinOp @11:9 left=<
              Number @11:7 value='1'>, op='<', right=<
              Number @11:11 value='2'>>>>,
          <ExprStatement @12:1 expr=<BinOp @12:3 left=<Number @12:1 value='1'>,
            op='|', right=<Number @12:5 value='2'>>>,
          <ExprStatement @13:1 expr=<Assign @13:5 left=<
            Identifier @13:1 value='bar'>, op='=', right=<BinOp @13:9 left=<
              Number @13:7 value='1'>, op='&', right=<
              Number @13:11 value='2'>>>>,
          <ExprStatement @14:1 expr=<BinOp @14:3 left=<Number @14:1 value='1'>,
            op='|', right=<BinOp @14:7 left=<Number @14:5 value='2'>,
              op='&', right=<Number @14:9 value='8'>>>>,
          <ExprStatement @15:1 expr=<Assign @15:5 left=<
            Identifier @15:1 value='bar'>, op='=', right=<BinOp @15:13 left=<
              BinOp @15:9 left=<Number @15:7 value='1'>, op='&', right=<
                Number @15:11 value='2'>>, op='|',
                  right=<Number @15:15 value='8'>>>>,
          <ExprStatement @16:1 expr=<BinOp @16:3 left=<
            Identifier @16:1 value='x'>, op='^', right=<
            Identifier @16:5 value='y'>>>,
          <ExprStatement @17:1 expr=<Assign @17:5 left=<
            Identifier @17:1 value='bar'>, op='=', right=<BinOp @17:9 left=<
              Identifier @17:7 value='x'>, op='^', right=<
              Identifier @17:11 value='y'>>>>,
          <ExprStatement @18:1 expr=<BinOp @18:3 left=<
            Identifier @18:1 value='x'>, op='&&', right=<
            Identifier @18:6 value='y'>>>,
          <ExprStatement @19:1 expr=<Assign @19:5 left=<
            Identifier @19:1 value='bar'>, op='=', right=<BinOp @19:9 left=<
              Identifier @19:7 value='x'>, op='&&', right=<
              Identifier @19:12 value='y'>>>>,
          <ExprStatement @20:1 expr=<Comma @20:2 left=<Number @20:1 value='1'>,
            right=<Number @20:3 value='2'>>>
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
        <Program @1:1 ?children=[<Try @1:1 catch=<
          Catch @3:3 elements=<Block @3:15 ?children=[
            <ExprStatement @4:3 expr=<Assign @4:5 left=<
              Identifier @4:3 value='x'>, op='=', right=<
                Identifier @4:7 value='exc'>>>
            ]>,
            identifier=<Identifier @3:10 value='exc'>
          >,
          fin=None,
          statements=<Block @1:5 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='x'>, op='=',
              right=<Number @2:7 value='3'>>>
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
        <Program @1:1 ?children=[<Try @1:1 catch=None,
          fin=<Finally @3:3 elements=<Block @3:11 ?children=[
            <ExprStatement @4:3 expr=<Assign @4:5 left=<
              Identifier @4:3 value='x'>, op='=', right=<
                Null @4:7 value='null'>>>
          ]>>,
          statements=<Block @1:5 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='x'>, op='=',
              right=<Number @2:7 value='3'>>>
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
        <Program @1:1 ?children=[<Try @1:1 catch=<
          Catch @3:3 elements=<Block @3:15 ?children=[
            <ExprStatement @4:3 expr=<Assign @4:5 left=<
              Identifier @4:3 value='x'>, op='=', right=<
                Identifier @4:7 value='exc'>>>
            ]>,
            identifier=<Identifier @3:10 value='exc'>
          >,
          fin=<Finally @5:3 elements=<Block @5:11 ?children=[
            <ExprStatement @6:3 expr=<Assign @6:5 left=<
              Identifier @6:3 value='y'>, op='=', right=<
                Null @6:7 value='null'>>>
          ]>>,
          statements=<Block @1:5 ?children=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='x'>, op='=',
              right=<Number @2:7 value='5'>>>
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
        <Program @1:1 ?children=[
          <FuncDecl @1:1 elements=[
            <ExprStatement @2:3 expr=<Assign @2:5 left=<
              Identifier @2:3 value='z'>, op='=', right=<
              Number @2:7 value='10'>>>,
            <Return @3:3 expr=<BinOp @3:16 left=<BinOp @3:12 left=<
                Identifier @3:10 value='x'>,
                op='+', right=<Identifier @3:14 value='y'>>,
              op='+', right=<Identifier @3:18 value='z'>>>
          ], identifier=<Identifier @1:10 value='foo'>, parameters=[
            <Identifier @1:14 value='x'>, <Identifier @1:17 value='y'>
          ]>
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
        <Program @1:1 ?children=[
          <FuncDecl @1:1 elements=[
            <Return @2:3 expr=<Number @2:10 value='10'>>],
            identifier=<Identifier @1:10 value='foo'>, parameters=[]>
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
        <Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
              initializer=<FuncExpr @1:9 elements=[
                <Return @2:3 expr=<Number @2:10 value='10'>>
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
        <Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
              initializer=<FuncExpr @1:9 elements=[
                <Return @2:3 expr=<BinOp @2:12 left=<
                  Identifier @2:10 value='x'>, op='+',
                  right=<Identifier @2:14 value='y'>>>
              ], identifier=<Identifier @1:18 value='foo'>, parameters=[
                <Identifier @1:22 value='x'>, <Identifier @1:25 value='y'>
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
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='x'>,
            initializer=<FuncExpr @1:9 elements=[],
              identifier=<Identifier @1:18 value='y'>, parameters=[]>>]>]>
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
        <Program @1:1 ?children=[<FuncDecl @1:1 elements=[
          <FuncDecl @2:3 elements=[], identifier=<
            Identifier @2:12 value='bar'>, parameters=[]>
        ], identifier=<Identifier @1:10 value='foo'>, parameters=[]>]>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<FunctionCall @1:1 args=<
            Arguments @1:4 items=[]>, identifier=<
            Identifier @1:1 value='foo'>>>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='r'>,
              initializer=<FunctionCall @2:9 args=<Arguments @2:12 items=[]>,
                identifier=<Identifier @2:9 value='foo'>>>]>
        ]>
        """,
    ), (
        'function_call_argument',
        """
        foo(x, 7);
        var r = foo(x, 7);
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<FunctionCall @1:1 args=<
            Arguments @1:4 items=[
              <Identifier @1:5 value='x'>, <Number @1:8 value='7'>
            ]>,
            identifier=<Identifier @1:1 value='foo'>>>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='r'>,
              initializer=<FunctionCall @2:9 args=<Arguments @2:12 items=[
                <Identifier @2:13 value='x'>, <Number @2:16 value='7'>
              ]>,
              identifier=<Identifier @2:9 value='foo'>>>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BracketAccessor @1:6 expr=<
              Number @1:7 value='10'>,
            node=<FunctionCall @1:1 args=<Arguments @1:4 items=[]>,
            identifier=<Identifier @1:1 value='foo'>>>>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='j'>,
              initializer=<BracketAccessor @2:14 expr=<
                Number @2:15 value='10'>, node=<FunctionCall @2:9 args=<
                Arguments @2:12 items=[]>,
                identifier=<Identifier @2:9 value='foo'>>>>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<DotAccessor @1:6 identifier=<
              PropIdentifier @1:7 value='foo'>,
            node=<FunctionCall @1:1 args=<Arguments @1:4 items=[]>,
            identifier=<Identifier @1:1 value='foo'>>>>,
            <VarStatement @2:1 ?children=[
              <VarDecl @2:5 identifier=<Identifier @2:5 value='bar'>,
                initializer=<DotAccessor @2:16 identifier=<
                  PropIdentifier @2:17 value='foo'>,
                node=<FunctionCall @2:11 args=<Arguments @2:14 items=[]>,
                  identifier=<Identifier @2:11 value='foo'>>>>
            ]>
        ]>
        """,
    ), (
        'new_keyword',
        """
        var foo = new Foo();
        """,
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='foo'>, initializer=<
            NewExpr @1:11 args=<Arguments @1:18 items=[]>,
            identifier=<Identifier @1:15 value='Foo'>>>
        ]>]>
        """,
    ), (
        # dot accessor
        'new_keyword_dot_accessor',
        'var bar = new Foo.Bar();',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='bar'>,
            initializer=<NewExpr @1:11 args=<Arguments @1:22 items=[]>,
              identifier=<DotAccessor @1:18 identifier=<
                PropIdentifier @1:19 value='Bar'>,
              node=<Identifier @1:15 value='Foo'>>>>
        ]>]>
        """,
    ), (
        # bracket accessor
        'new_keyword_bracket_accessor',
        'var bar = new Foo.Bar()[7];',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='bar'>,
            initializer=<BracketAccessor @1:24 expr=<Number @1:25 value='7'>,
              node=<NewExpr @1:11 args=<Arguments @1:22 items=[]>, identifier=<
                DotAccessor @1:18 identifier=<
                  PropIdentifier @1:19 value='Bar'>,
                node=<Identifier @1:15 value='Foo'>>>>>
        ]>]>
        """,

    ), (
        'new_keyword_in_object_slimit_78',
        """
        var foo = {
          key: {
            old: new new mod.Item(),
            new: new mod.Item()
          }
        };
        """,
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='foo'>,
            initializer=<Object @1:11 properties=[
              <Assign @2:6 left=<PropIdentifier @2:3 value='key'>,
                op=':', right=<Object @2:8 properties=[
                  <Assign @3:8 left=<PropIdentifier @3:5 value='old'>,
                    op=':', right=<NewExpr @3:10 args=None,
                      identifier=<NewExpr @3:14 args=<Arguments @3:26 items=[
                      ]>,
                      identifier=<DotAccessor @3:21 identifier=<
                        PropIdentifier @3:22 value='Item'>,
                        node=<Identifier @3:18 value='mod'>>>>>,
                  <Assign @4:8 left=<PropIdentifier @4:5 value='new'>,
                    op=':', right=<NewExpr @4:10 args=<Arguments @4:22 items=[
                    ]>,
                    identifier=<DotAccessor @4:17 identifier=<
                      PropIdentifier @4:18 value='Item'>,
                      node=<Identifier @4:14 value='mod'>>>>
                ]>>
            ]>>
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
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='obj'>, initializer=<
            Object @1:11 properties=[
              <Assign @2:6 left=<PropIdentifier @2:3 value='foo'>, op=':',
                right=<Number @2:8 value='10'>>,
              <Assign @3:6 left=<PropIdentifier @3:3 value='bar'>, op=':',
                right=<Number @3:8 value='20'>>
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
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='obj'>, initializer=<
            Object @1:11 properties=[
              <Assign @2:4 left=<Number @2:3 value='1'>, op=':', right=<
                String @2:6 value="'a'">>,
              <Assign @3:4 left=<Number @3:3 value='2'>, op=':', right=<
                String @3:6 value="'b'">>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<NewExpr @1:1 args=<
            Arguments @1:6 items=[]>, identifier=<
            Identifier @1:5 value='T'>>>,
          <ExprStatement @2:1 expr=<DotAccessor @2:8 identifier=<
            PropIdentifier @2:9 value='derp'>, node=<
              NewExpr @2:1 args=<Arguments @2:6 items=[]>,
              identifier=<Identifier @2:5 value='T'>>>>
        ]>
        """
    ), (
        'new_expr_args',
        """
        new T(arg1, arg2)
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<NewExpr @1:1 args=<Arguments @1:6 items=[
            <Identifier @1:7 value='arg1'>,
            <Identifier @1:13 value='arg2'>
          ]>,
          identifier=<Identifier @1:5 value='T'>>>
        ]>
        """
    ), (
        'new_new_expr',
        # a function that returns a function, then used as a constructor
        # var T = function(){ return function (){} }
        """
        new new T()
        var x = new new T()
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<NewExpr @1:1 args=None, identifier=<
            NewExpr @1:5 args=<Arguments @1:10 items=[]>, identifier=<
              Identifier @1:9 value='T'>>>>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='x'>,
              initializer=<NewExpr @2:9 args=None, identifier=<
                NewExpr @2:13 args=<Arguments @2:18 items=[]>,
                  identifier=<Identifier @2:17 value='T'>>>>
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
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='obj'>, initializer=<
            Object @1:11 properties=[
              <Assign @2:6 left=<String @2:3 value="'a'">, op=':', right=<
                Number @2:8 value='100'>>,
              <Assign @3:6 left=<String @3:3 value="'b'">, op=':', right=<
                Number @3:8 value='200'>>
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
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='obj'>,
            initializer=<Object @1:11 properties=[]>>
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
        <Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier @1:5 value='obj'>,
              initializer=<Object @1:11 properties=[
                <Assign @1:15 left=<PropIdentifier @1:12 value='foo'>, op=':',
                  right=<Number @1:17 value='1'>>
                ]>>
          ]>,
          <ExprStatement @2:1 expr=<UnaryExpr @2:1 op='delete',
            value=<DotAccessor @2:11 identifier=<
              PropIdentifier @2:12 value='foo'>,
              node=<Identifier @2:8 value='obj'>>>>
        ]>
        """,
    ), (
        'void_keyword',
        """
        void 0;
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<UnaryExpr @1:1 op='void',
            value=<Number @1:6 value='0'>>>
        ]>
        """,
    ), (
        # array
        'array_create_access',
        """
        var a = [1,2,3,4,5];
        var b = [1,];
        var c = [1,,];
        var d = [1,,,];
        var e = [1,,,,];
        var res = a[3];
        """,
        """
        <Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
              initializer=<Array @1:9 items=[
                <Number @1:10 value='1'>, <Number @1:12 value='2'>,
                <Number @1:14 value='3'>, <Number @1:16 value='4'>,
                <Number @1:18 value='5'>
              ]>>
          ]>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='b'>,
              initializer=<Array @2:9 items=[<Number @2:10 value='1'>
            ]>>
          ]>,
          <VarStatement @3:1 ?children=[
            <VarDecl @3:5 identifier=<Identifier @3:5 value='c'>, initializer=<
              Array @3:9 items=[
                <Number @3:10 value='1'>, <Elision @3:12 value=1>
              ]>>
          ]>,
          <VarStatement @4:1 ?children=[
            <VarDecl @4:5 identifier=<Identifier @4:5 value='d'>, initializer=<
              Array @4:9 items=[
                <Number @4:10 value='1'>, <Elision @4:12 value=2>
              ]>>
          ]>,
          <VarStatement @5:1 ?children=[
            <VarDecl @5:5 identifier=<Identifier @5:5 value='e'>, initializer=<
              Array @5:9 items=[
                <Number @5:10 value='1'>, <Elision @5:12 value=3>
              ]>>
          ]>,
          <VarStatement @6:1 ?children=[
            <VarDecl @6:5 identifier=<Identifier @6:5 value='res'>,
              initializer=<BracketAccessor @6:12 expr=<Number @6:13 value='3'>,
                node=<Identifier @6:11 value='a'>>>
          ]>
        ]>
        """,
    ), (
        # elision
        'elision_1',
        'var a = [,,,];',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
            initializer=<Array @1:9 items=[
              <Elision @1:10 value=3>
            ]>>
          ]>
        ]>
        """,
    ), (
        'elision_2',
        'var a = [1,,,4];',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
            initializer=<Array @1:9 items=[
              <Number @1:10 value='1'>,
              <Elision @1:12 value=2>,
              <Number @1:14 value='4'>
            ]>>
          ]>
        ]>
        """,
    ), (
        'elision_3',
        'var a = [1,,3,,5];',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
            initializer=<Array @1:9 items=[
              <Number @1:10 value='1'>,
              <Elision @1:12 value=1>,
              <Number @1:13 value='3'>,
              <Elision @1:15 value=1>,
              <Number @1:16 value='5'>
            ]>>
          ]>
        ]>
        """,
    ), (
        'elision_4',
        'var a = [1,,,,];',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
            initializer=<Array @1:9 items=[
              <Number @1:10 value='1'>,
              <Elision @1:12 value=3>
            ]>>
          ]>
        ]>
        """,
    ), (
        'elision_5',
        'var a = [,,,, 1];',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='a'>,
            initializer=<Array @1:9 items=[
              <Elision @1:10 value=4>,
              <Number @1:15 value='1'>
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
        <Program @1:1 ?children=[<ExprStatement @1:1 expr=<
          BinOp @1:25 left=<DotAccessor @1:17 identifier=<
            PropIdentifier @1:18 value='source'>,
            node=<BracketAccessor @1:11 expr=<Identifier @1:12 value='type'>,
              node=<DotAccessor @1:5 identifier=<
                PropIdentifier @1:6 value='match'>, node=<
                  Identifier @1:1 value='Expr'>>>>,
          op='+', right=<GroupingOp @1:27 expr=<
            DotAccessor @1:54 identifier=<PropIdentifier @1:55 value='source'>,
              node=<Regex @1:28 value='/(?![^\\[]*\\])(?![^\\(]*\\))/'>>>>>
        ]>
        """,
    ), (
        'comparison',
        '(options = arguments[i]) != null;',
        # test 54
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:26 left=<GroupingOp @1:1 expr=
            <Assign @1:10 left=<
              Identifier @1:2 value='options'>, op='=',
              right=<BracketAccessor @1:21 expr=<Identifier @1:22 value='i'>,
            node=<Identifier @1:12 value='arguments'>>>>,
            op='!=', right=<Null @1:29 value='null'>>>
        ]>
        """,
    ), (
        'regex_test',
        r'return (/h\d/i).test(elem.nodeName);',
        r"""
        <Program @1:1 ?children=[<Return @1:1 expr=<FunctionCall @1:8 args=<
          Arguments @1:21 items=[
            <DotAccessor @1:26 identifier=<
              PropIdentifier @1:27 value='nodeName'>,
              node=<Identifier @1:22 value='elem'>>
          ]>,
          identifier=<
            DotAccessor @1:16 identifier=<PropIdentifier @1:17 value='test'>,
            node=<GroupingOp @1:8 expr=<Regex @1:9 value='/h\\d/i'>>>>>]>

        """,

    ), (
        'slash_as_regex_after_block',
        '{}/a/g',
        r"""
        <Program @1:1 ?children=[
          <Block @1:1 >,
          <ExprStatement @1:3 expr=<Regex @1:3 value='/a/g'>>
        ]>
        """,

    ), (
        'slash_as_div_after_plus_brace',
        '+{}/a/g',
        r"""
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:6 left=<BinOp @1:4 left=<
                UnaryExpr @1:1 op='+', value=<Object @1:2 properties=[]>>,
              op='/',
              right=<Identifier @1:5 value='a'>>,
            op='/', right=<Identifier @1:7 value='g'>>>
        ]>
        """,

    ), (
        'slash_as_regex_after_plus_plus_as_unary',
        '++/a/.b',
        r"""
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<UnaryExpr @1:1 op='++',
            value=<DotAccessor @1:6 identifier=<PropIdentifier @1:7 value='b'>,
              node=<Regex @1:3 value='/a/'>>>>
        ]>
        """,
    ), (
        'slash_as_div_after_plus_plus_as_postfix_expr',
        'i++/a/b',
        r"""
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:6 left=<BinOp @1:4 left=<
                PostfixExpr @1:2 op='++', value=<Identifier @1:1 value='i'>>,
              op='/', right=<Identifier @1:5 value='a'>>,
            op='/', right=<Identifier @1:7 value='b'>>>
        ]>
        """,
    ), (
        'slash_as_regex_after_minus_minus_as_unary',
        '--/a/.b',
        r"""
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<UnaryExpr @1:1 op='--',
            value=<DotAccessor @1:6 identifier=<PropIdentifier @1:7 value='b'>,
              node=<Regex @1:3 value='/a/'>>>>
        ]>
        """,
    ), (
        'slash_as_div_after_minus_minus_as_postfix_expr',
        'i--/a/b',
        r"""
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:6 left=<BinOp @1:4 left=<
                PostfixExpr @1:2 op='--', value=<Identifier @1:1 value='i'>>,
              op='/', right=<Identifier @1:5 value='a'>>,
            op='/', right=<Identifier @1:7 value='b'>>>
        ]>
        """,
    ), (
        'slash_as_regex_after_function',
        """
        if (0) {
        }
        /foo/g
        """,
        r"""
        <Program @1:1 ?children=[
          <If @1:1 alternative=None, consequent=<Block @1:8 >,
            predicate=<Number @1:5 value='0'>>,
          <ExprStatement @3:1 expr=<Regex @3:1 value='/foo/g'>>
        ]>
        """,

    ), (
        'slash_as_regex_after_function_block',
        """
        (function() {})()
        var v = f(5) / f(5);
        """,
        r"""
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<FunctionCall @1:1 args=<
             Arguments @1:16 items=[]>,
            identifier=<GroupingOp @1:1 expr=<FuncExpr @1:2 elements=[],
                identifier=None, parameters=[]>>>>,
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='v'>,
              initializer=<BinOp @2:14 left=<FunctionCall @2:9 args=<
                  Arguments @2:10 items=[
                    <Number @2:11 value='5'>
                  ]>,
                identifier=<Identifier @2:9 value='f'>>,
                op='/', right=<FunctionCall @2:16 args=<
                  Arguments @2:17 items=[
                    <Number @2:18 value='5'>
                  ]>, identifier=<Identifier @2:16 value='f'>>
              >
            >
          ]>
        ]>
        """,

    ), (
        # https://github.com/rspivak/slimit/issues/42
        'slimit_issue_42',
        """
        e.b(d) ? (a = [c.f(j[1])], e.fn.attr.call(a, d, !0)) : a = [k.f(j[1])];
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<Conditional @1:8 alternative=<
              Assign @1:58 left=<Identifier @1:56 value='a'>, op='=',
              right=<Array @1:60 items=[
            <FunctionCall @1:61 args=<Arguments @1:64 items=[
              <BracketAccessor @1:66 expr=<Number @1:67 value='1'>,
                node=<Identifier @1:65 value='j'>>
            ]>, identifier=<DotAccessor @1:62 identifier=<
              PropIdentifier @1:63 value='f'>,
              node=<Identifier @1:61 value='k'>>>
          ]>>,
          consequent=<GroupingOp @1:10 expr=<Comma @1:26 left=<
                Assign @1:13 left=<Identifier @1:11 value='a'>, op='=',
              right=<Array @1:15 items=[
                <FunctionCall @1:16 args=<Arguments @1:19 items=[
                  <BracketAccessor @1:21 expr=<Number @1:22 value='1'>,
                    node=<Identifier @1:20 value='j'>>
                ]>, identifier=<DotAccessor @1:17 identifier=<
                  PropIdentifier @1:18 value='f'>,
                  node=<Identifier @1:16 value='c'>>>
              ]>>,
            right=<FunctionCall @1:28 args=<Arguments @1:42 items=[
                <Identifier @1:43 value='a'>,
                <Identifier @1:46 value='d'>,
                <UnaryExpr @1:49 op='!', value=<
                  Number @1:50 value='0'>>
              ]>,
              identifier=<DotAccessor @1:37 identifier=<
                PropIdentifier @1:38 value='call'>, node=<
                  DotAccessor @1:32 identifier=<
                      PropIdentifier @1:33 value='attr'>,
                    node=<DotAccessor @1:29 identifier=<
                      PropIdentifier @1:30 value='fn'>,
                        node=<Identifier @1:28 value='e'>>>>>>>,
          predicate=<FunctionCall @1:1 args=<Arguments @1:4 items=[
            <Identifier @1:5 value='d'>
          ]>, identifier=<DotAccessor @1:2 identifier=<
            PropIdentifier @1:3 value='b'>, node=<Identifier @1:1 value='e'>>
          >>>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<GroupingOp @1:1 expr=<
            FunctionCall @1:2 args=<Arguments @3:2 items=[]>,
            identifier=<FuncExpr @1:2 elements=[
              <ExprStatement @2:3 expr=<Assign @2:5 left=<
                Identifier @2:3 value='x'>, op='=',
                right=<Number @2:7 value='5'>>>
            ],
            identifier=None, parameters=[]>>>>
        ]>
        """,
    ), (
        'return_statement_negation',
        'return !(match === true || elem.getAttribute("classid") !== match);',
        """
        <Program @1:1 ?children=[<Return @1:1 expr=<
          UnaryExpr @1:8 op='!',
            value=<GroupingOp @1:9 expr=<BinOp @1:25 left=<
              BinOp @1:16 left=<Identifier @1:10 value='match'>, op='===',
                right=<Boolean @1:20 value='true'>>, op='||', right=<
            BinOp @1:57 left=<FunctionCall @1:28 args=<Arguments @1:45 items=[
              <String @1:46 value='"classid"'>
            ]>,
            identifier=<DotAccessor @1:32 identifier=<
              PropIdentifier @1:33 value='getAttribute'>, node=<
                Identifier @1:28 value='elem'>>>, op='!==', right=<
                  Identifier @1:61 value='match'>>>>>>
        ]>
        """,
    ), (
        # test 57
        'ternary_dot_accessor',
        'var el = (elem ? elem.ownerDocument || elem : 0).documentElement;',
        """
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='el'>,
            initializer=<DotAccessor @1:49 identifier=<
              PropIdentifier @1:50 value='documentElement'>,
              node=<GroupingOp @1:10 expr=<Conditional @1:16 alternative=<
                Number @1:47 value='0'>,
                consequent=<BinOp @1:37 left=<DotAccessor @1:22 identifier=<
                  PropIdentifier @1:23 value='ownerDocument'>,
                  node=<Identifier @1:18 value='elem'>
                >, op='||', right=<Identifier @1:40 value='elem'>>,
            predicate=<Identifier @1:11 value='elem'>>>>
          >
        ]>]>
        """,
    ), (
        # typeof
        'typeof',
        'typeof second.length === "number";',
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:22 left=<
            UnaryExpr @1:1 op='typeof', value=<DotAccessor @1:14 identifier=
              <PropIdentifier @1:15 value='length'>, node=<
                Identifier @1:8 value='second'>>>,
            op='===', right=<String @1:26 value='"number"'
          >>>
        ]>
        """,
    ), (
        'instanceof',
        'x instanceof y',
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:3 left=<
            Identifier @1:1 value='x'>,
            op='instanceof', right=<Identifier @1:14 value='y'>>>
        ]>
        """,
    ), (
        # membership
        'membership_in',
        """
        1 in s;
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:3 left=<Number @1:1 value='1'>,
            op='in', right=<Identifier @1:6 value='s'>>>
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
        <Program @1:1 ?children=[
          <For @1:1 cond=
            <ExprStatement @1:11 expr=
              <BinOp @1:13 left=<Identifier @1:11 value='i'>,
                op='<', right=<Number @1:15 value='3'>>>,
            count=<PostfixExpr @1:19 op='++',
              value=<Identifier @1:18 value='i'>>,
            init=<ExprStatement @1:6 expr=<FunctionCall @1:6 args=<
              Arguments @1:7 items=[]>,
              identifier=<Identifier @1:6 value='o'>>>,
            statement=<Block @1:23 >>
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
        for (var x, y, z;;);
        """,
        """
        <Program @1:1 ?children=[
          <For @1:1 cond=<EmptyStatement @1:18 value=';'>, count=None,
            init=<ExprStatement @1:6 expr=<BinOp @1:8 left=<
              Identifier @1:6 value='o'>, op='<',
              right=<GroupingOp @1:10 expr=<BinOp @1:13 left=<
                Identifier @1:11 value='p'>, op='<',
                right=<Identifier @1:15 value='q'>>>>>,
            statement=<EmptyStatement @1:20 value=';'>>,
          <For @2:1 cond=<EmptyStatement @2:20 value=';'>, count=None,
            init=<ExprStatement @2:6 expr=<BinOp @2:8 left=<
              Identifier @2:6 value='o'>, op='==', right=<
                GroupingOp @2:11 expr=<BinOp @2:14 left=<
                  Identifier @2:12 value='p'>, op='==',
                  right=<Identifier @2:17 value='q'>>>>>,
            statement=<EmptyStatement @2:22 value=';'>>,
          <For @3:1 cond=<EmptyStatement @3:18 value=';'>, count=None,
            init=<ExprStatement @3:6 expr=<BinOp @3:8 left=<
              Identifier @3:6 value='o'>, op='^',
              right=<GroupingOp @3:10 expr=<BinOp @3:13 left=<
                Identifier @3:11 value='p'>, op='^',
                right=<Identifier @3:15 value='q'>>>>>,
            statement=<EmptyStatement @3:20 value=';'>>,
          <For @4:1 cond=<EmptyStatement @4:18 value=';'>, count=None, init=<
            ExprStatement @4:6 expr=<BinOp @4:8 left=<
              Identifier @4:6 value='o'>, op='|',
              right=<GroupingOp @4:10 expr=<BinOp @4:13 left=<
                Identifier @4:11 value='p'>, op='|',
                  right=<Identifier @4:15 value='q'>>>>>,
            statement=<EmptyStatement @4:20 value=';'>>,
          <For @5:1 cond=<EmptyStatement @5:18 value=';'>, count=None, init=<
            ExprStatement @5:6 expr=<BinOp @5:8 left=<
              Identifier @5:6 value='o'>, op='&',
              right=<GroupingOp @5:10 expr=<BinOp @5:13 left=<
                Identifier @5:11 value='p'>, op='&', right=<
                Identifier @5:15 value='q'>>>>>,
            statement=<EmptyStatement @5:20 value=';'>>,
          <For @6:1 cond=<EmptyStatement @6:30 value=';'>, count=None, init=<
            ExprStatement @6:6 expr=<Conditional @6:8 alternative=<
              Boolean @6:24 value='false'>,
              consequent=<GroupingOp @6:10 expr=<
                Conditional @6:13 alternative=<Identifier @6:19 value='d'>,
                consequent=<Identifier @6:15 value='c'>,
                predicate=<Identifier @6:11 value='b'>>>,
              predicate=<Identifier @6:6 value='a'>>>,
            statement=<EmptyStatement @6:32 value=';'>>,
          <For @7:1 cond=<EmptyStatement @7:12 value=';'>, count=None, init=<
            VarStatement @7:6 ?children=[
              <VarDecl @7:10 identifier=<Identifier @7:10 value='x'>,
                initializer=None>
              ]>,
            statement=<EmptyStatement @7:14 value=';'>>,
          <For @8:1 cond=<EmptyStatement @8:18 value=';'>, count=None, init=<
            VarStatement @8:6 ?children=[
              <VarDecl @8:10 identifier=<Identifier @8:10 value='x'>,
                initializer=None>,
              <VarDecl @8:13 identifier=<Identifier @8:13 value='y'>,
                initializer=None>,
              <VarDecl @8:16 identifier=<Identifier @8:16 value='z'>,
                initializer=None>
              ]>,
            statement=<EmptyStatement @8:20 value=';'>>
        ]>
        """,

    ), (
        'for_initializer_noin',
        """
        for (var x = foo() in (bah())) {};
        """,
        """
        <Program @1:1 ?children=[
          <ForIn @1:1 item=<VarDeclNoIn @1:6 identifier=<
                Identifier @1:10 value='x'>,
              initializer=<FunctionCall @1:14 args=<Arguments @1:17 items=[
              ]>,
              identifier=<Identifier @1:14 value='foo'>>>,
            iterable=<GroupingOp @1:23 expr=<FunctionCall @1:24 args=<
              Arguments @1:27 items=[]>,
              identifier=<Identifier @1:24 value='bah'>>>,
            statement=<Block @1:32 >>,
          <EmptyStatement @1:34 value=';'>
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
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<Assign @1:16 left=<
              DotAccessor @1:5 identifier=<
                PropIdentifier @1:6 value='prototype'>,
                node=<Identifier @1:1 value='Name'>>,
              op='=', right=<Object @1:18 properties=[
                <GetPropAssign @2:3 elements=[
                  <Return @3:5 expr=<BinOp @3:29 left=<BinOp @3:23 left=<
                      DotAccessor @3:16 identifier=<
                        PropIdentifier @3:17 value='first'>,
                        node=<This @3:12 >>,
                      op='+', right=<String @3:25 value='" "'>>,
                    op='+', right=<DotAccessor @3:35 identifier=<
                      PropIdentifier @3:36 value='last'>, node=<This @3:31 >>>>
                ],
                prop_name=<PropIdentifier @2:7 value='fullName'>>,
                <SetPropAssign @5:3 elements=[
                  <VarStatement @6:5 ?children=[
                    <VarDecl @6:9 identifier=<Identifier @6:9 value='names'>,
                      initializer=<FunctionCall @6:17 args=<
                        Arguments @6:27 items=[
                          <String @6:28 value='" "'>
                        ]>,
                        identifier=<DotAccessor @6:21 identifier=<
                        PropIdentifier @6:22 value='split'>, node=<
                        Identifier @6:17 value='name'>>>>
                  ]>,
                  <ExprStatement @7:5 expr=<Assign @7:16 left=<
                    DotAccessor @7:9 identifier=<
                      PropIdentifier @7:10 value='first'>, node=<This @7:5 >>,
                    op='=', right=<BracketAccessor @7:23 expr=<
                      Number @7:24 value='0'>, node=<
                        Identifier @7:18 value='names'>>>>,
                  <ExprStatement @8:5 expr=<Assign @8:15 left=<
                    DotAccessor @8:9 identifier=<
                      PropIdentifier @8:10 value='last'>, node=<This @8:5 >>,
                      op='=', right=<BracketAccessor @8:22 expr=<
                        Number @8:23 value='1'>,
                          node=<Identifier @8:17 value='names'>>>>
                ],
                parameter=<Identifier @5:16 value='name'>,
                prop_name=<PropIdentifier @5:7 value='fullName'>>
          ]>>>
        ]>
        """,
    ), (
        'dot_accessor_on_integer',
        """
        (0).toString();
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<FunctionCall @1:1 args=<
              Arguments @1:13 items=[]>,
            identifier=<DotAccessor @1:4 identifier=<
              PropIdentifier @1:5 value='toString'>,
              node=<GroupingOp @1:1 expr=<Number @1:2 value='0'>>>>>
        ]>
        """,
    ), (
        'dot_reserved_word',
        """
        e.case;
        """,
        """
        <Program @1:1 ?children=[<ExprStatement @1:1 expr=<
          DotAccessor @1:2 identifier=<PropIdentifier @1:3 value='case'>,
          node=<Identifier @1:1 value='e'>>>
        ]>
        """
    ), (
        'dot_reserved_word_nobf',
        """
        for (x = e.case;;);
        """,
        """
        <Program @1:1 ?children=[
          <For @1:1 cond=<EmptyStatement @1:17 value=';'>,
            count=None, init=<ExprStatement @1:6 expr=<Assign @1:8 left=<
              Identifier @1:6 value='x'>, op='=', right=<
                DotAccessor @1:11 identifier=<
                  PropIdentifier @1:12 value='case'>,
                node=<Identifier @1:10 value='e'>>>>,
            statement=<EmptyStatement @1:19 value=';'>>
        ]>
        """
    ), (
        'logical_or_expr_nobf',
        """
        (true || true) || (false && false);
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:16 left=<
              GroupingOp @1:1 expr=<BinOp @1:7 left=<
                Boolean @1:2 value='true'>, op='||', right=<
                Boolean @1:10 value='true'>>>,
            op='||', right=<
              GroupingOp @1:19 expr=<BinOp @1:26 left=<
                Boolean @1:20 value='false'>, op='&&', right=<
                Boolean @1:29 value='false'>>>>>
        ]>
        """,
    ), (
        'multiplicative_expr_nobf',
        """
        !0 % 1
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<BinOp @1:4 left=<UnaryExpr @1:1 op='!',
              value=<Number @1:2 value='0'>>,
            op='%', right=<Number @1:6 value='1'>>>
        ]>
        """
    ), (
        'function_expr_1',
        """
        (function(arg) {});
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<GroupingOp @1:1 expr=<
            FuncExpr @1:2 elements=[],
              identifier=None, parameters=[<Identifier @1:11 value='arg'>]>>>
        ]>
        """
    ), (
        'octal_slimit_issue_70',
        r"var x = '\071[90m%s';",
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='x'>, initializer=<
            String @1:9 value="'\\071[90m%s'">>
        ]>]>
        """
    ), (
        'special_array_char_slimit_issue_82',
        r"var x = ['a','\n'];",
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='x'>,
            initializer=<Array @1:9 items=[
              <String @1:10 value="'a'">,
              <String @1:14 value="'\\n'">
            ]>
          >
        ]>]>
        """
    ), (
        'special_string_slimit_issue_82',
        r"var x = '\n';",
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='x'>,
            initializer=<String @1:9 value="'\\n'">>
        ]>]>
        """
    ), (
        'for_in_without_braces',
        "for (index in [1,2,3]) index",
        """
        <Program @1:1 ?children=[
          <ForIn @1:1 item=<Identifier @1:6 value='index'>,
            iterable=<Array @1:15 items=[
              <Number @1:16 value='1'>,
              <Number @1:18 value='2'>,
              <Number @1:20 value='3'>
            ]>,
            statement=<ExprStatement @1:24 expr=<
              Identifier @1:24 value='index'>>>
        ]>
        """
    ), (
        'for_loop_into_regex_slimit_issue_54',
        # "for (index in [1,2,3]) /^salign$/i.test('salign')",
        "for (index in [1,2,3]) /^salign$/",
        """
        <Program @1:1 ?children=[
          <ForIn @1:1 item=<Identifier @1:6 value='index'>,
            iterable=<Array @1:15 items=[
              <Number @1:16 value='1'>,
              <Number @1:18 value='2'>,
              <Number @1:20 value='3'>
            ]>,
            statement=<ExprStatement @1:24 expr=<
              Regex @1:24 value='/^salign$/'>>>
        ]>
        """
    ), (
        'parse_closure_scope',
        """
        (function() {
          x = 5;
        }());
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<GroupingOp @1:1 expr=<
            FunctionCall @1:2 args=<Arguments @3:2 items=[]>, identifier=<
              FuncExpr @1:2 elements=[
                <ExprStatement @2:3 expr=<Assign @2:5 left=<
                  Identifier @2:3 value='x'>, op='=',
                  right=<Number @2:7 value='5'>>>
              ],
              identifier=None, parameters=[]>>>>
        ]>
        """,
    ), (
        'excessive_grouping_normalized',
        """
        ((((value)))).toString();
        """,
        """
        <Program @1:1 ?children=[
          <ExprStatement @1:1 expr=<FunctionCall @1:1 args=<
            Arguments @1:23 items=[]>,
            identifier=<DotAccessor @1:14 identifier=<
              PropIdentifier @1:15 value='toString'>,
              node=<GroupingOp @1:4 expr=<Identifier @1:5 value='value'>>>>>
        ]>
        """
    ), (
        'crlf_lineno',
        """
        var dummy = function() {\r\n    return 0;\r\n};
        """,
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='dummy'>,
            initializer=<FuncExpr @1:13 elements=[
              <Return @2:5 expr=<Number @2:12 value='0'>>
            ], identifier=None, parameters=[]>
          >
        ]>]>
        """
    ), (
        'nlcr_lineno',
        """
        var dummy = function() {\n\r    return 0;\n\r};
        """,
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='dummy'>,
            initializer=<FuncExpr @1:13 elements=[
              <Return @3:5 expr=<Number @3:12 value='0'>>
            ], identifier=None, parameters=[]>
          >
        ]>]>
        """
    ), (
        'crlf_lineno_line_cont',
        """
        var dummy = function() {\r\n  var r = '\\\r\n  ';\r\n  return r;\r\n};
        """,
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='dummy'>,
            initializer=<FuncExpr @1:13 elements=[
              <VarStatement @2:3 ?children=[
                <VarDecl @2:7 identifier=<Identifier @2:7 value='r'>,
                  initializer=<String @2:11 value="'\\\r\n  '">>
                ]>,
              <Return @4:3 expr=<Identifier @4:10 value='r'>>
            ],
            identifier=None, parameters=[]>
          >
        ]>]>
        """
    ), (
        'cr_lineno',
        """
        var dummy = function() {\r    return 0;\r};
        """,
        r"""
        <Program @1:1 ?children=[<VarStatement @1:1 ?children=[
          <VarDecl @1:5 identifier=<Identifier @1:5 value='dummy'>,
            initializer=<FuncExpr @1:13 elements=[
              <Return @2:5 expr=<Number @2:12 value='0'>>
            ], identifier=None, parameters=[]>
          >
        ]>]>
        """
    )]))


# ASI - Automatic Semicolon Insertion


def build_asi_test_cases(clsname, parse, pretty_print):
    def regenerate(value):
        return pretty_print(parse(value))

    return build_equality_testcase(clsname, regenerate, ((
        label,
        textwrap.dedent(argument).lstrip(),
        textwrap.dedent(result).lstrip(),
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
        [true, false, null, undefined];
        """
    ), (
        'while_empty',
        """
        while (true);
        """,
        """
        while (true);
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
        'new_new_expr',
        """
        new new T()
        var x = new new T()
        new new T(a1, a2, a3)
        var y = new new T(a1, a2, a3)
        """,
        """
        new new T();
        var x = new new T();
        new new T(a1, a2, a3);
        var y = new new T(a1, a2, a3);
        """,
    ), (
        'for_loop_first_empty',
        """
        for (; i < length; i++) {
        }
        """,
        """
        for (; i < length; i++) {
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
        }
        catch (e) {
        }
        finally {
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
        foo = [1, 2, 3][1];
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
    ), (
        'new_keyword_in_object_slimit_78',
        """
        var foo = {
          key: {
            old: new new mod.Item(),
            new: new mod.Item()
          }
        }
        """,
        """
        var foo = {
          key: {
            old: new new mod.Item(),
            new: new mod.Item()
          }
        };
        """,
    ), (
        'slimit_78',
        """
        $$thing('set', 'thing', {
          true: '-1',
          false: '0'
        })
        """,
        """
        $$thing('set', 'thing', {
          true: '-1',
          false: '0'
        });
        """,
    )]))


def build_syntax_error_test_cases(clsname, parse):
    return build_exception_testcase(clsname, parse, ((
        label,
        textwrap.dedent(argument).strip(),
        msg,
    ) for label, argument, msg in [(
        'interger_unwrapped_raw_dot_accessor',
        '0.toString();',
        "Unexpected 'toString' at 1:3 between '0.' at 1:1 and '(' at 1:11",
    ), (
        'unterminated_comment',  # looks like regex
        's = /****/;',
        "Unexpected ';' at 1:11 after '=' at 1:3",
    ), (
        # expression is not optional in throw statement
        # ASI at lexer level should insert ';' after throw
        'throw_error_asi',
        """
        throw
          'exc';
        """,
        "Unexpected \"'exc'\" at 2:3 after 'throw' at 1:1",
    ), (
        # note that the line continuation do not swallow
        'throw_error_after_line_continuation_lineno',
        r"""
        s = 'something \
        '
        throw;
        """,
        "Unexpected ';' at 3:6 after 'throw' at 3:1",
    ), (
        'setter_single_arg',
        """
        Name.prototype = {
          set failure(arg1, arg2) {
            return {1:{2:{3:{4:4}}}};
          }
        };
        """,
        "Unexpected ',' at 2:19 between 'arg1' at 2:15 and 'arg2' at 2:21",
    ), (
        'bare_function_expr',
        """
        function(arg) {};
        """,
        "Function statement requires a name at 1:9",
    ), (
        # potential to be pathological for backtracking as it will never
        # form a regex
        'slash_after_block_incomplete',
        """
        {}/
        """,
        "Unexpected '/' at 1:3 after '}' at 1:2",
    ), (
        'slash_after_block_fail_regex',
        """
        {}/function{;
        """,
        "Error parsing regular expression '/function{;' at 1:3",
    ), (
        'backtrack_not_mess_up_line_locations',
        """
        {}
        /a/
          function(arg) {};
        """,
        "Function statement requires a name at 3:11",
    )]), ECMASyntaxError)


def build_regex_syntax_error_test_cases(clsname, parse):
    return build_exception_testcase(clsname, parse, ((
        label,
        textwrap.dedent(argument).strip(),
        msg,
    ) for label, argument, msg in [(
        'unmatched_brackets',
        'var x = /][/;',
        "Error parsing regular expression '/][/;' at 1:9",
    ), (
        'unmatched_backslash',
        r'var x = /\/;',
        r"Error parsing regular expression '/\/;' at 1:9",
    )]), ECMARegexSyntaxError)


def build_comments_test_cases(clsname, parse, program_type):

    def parse_with_comments_to_repr(value):
        return repr_walker.walk(parse(value, with_comments=True), pos=True)

    return build_equality_testcase(clsname, parse_with_comments_to_repr, ((
        label,
        textwrap.dedent(argument).strip(),
        format_repr_program_type(label, result, program_type),
    ) for label, argument, result in [(
        'block_without_comments',
        """
        {
          var a = 5;
        }
        """,
        """
        <Program @1:1 ?children=[
          <Block @1:1 ?children=[<VarStatement @2:3 ?children=[
            <VarDecl @2:7 identifier=<Identifier @2:7 value='a'>,
              initializer=<Number @2:11 value='5'>>
          ]>]>
        ]>
        """,
    ), (
        'block_with_comments',
        """
        // hi
        // this is a test
        {
          // comment
          var/* inline block note */a = 5;
        }
        """,
        """
        <Program @3:1 ?children=[
          <Block @3:1 ?children=[
            <VarStatement @5:3 ?children=[
              <VarDecl @5:29 identifier=<Identifier @5:29 comments=<
                Comments @5:6 ?children=[
                  <BlockComment @5:6 value='/* inline block note */'>
                ]
              >, value='a'>, initializer=<Number @5:33 value='5'>>
            ], comments=<Comments @4:3 ?children=[
              <LineComment @4:3 value='// comment'>
            ]>>
          ], comments=<Comments @1:1 ?children=[
            <LineComment @1:1 value='// hi'>,
            <LineComment @2:1 value='// this is a test'>
          ]>>
        ]>
        """,
    ), (
        'variable_statement',
        """
        // hello
        var a;
        """,
        """
        <Program @2:1 ?children=[
          <VarStatement @2:1 ?children=[
            <VarDecl @2:5 identifier=<Identifier @2:5 value='a'>,
              initializer=None>
          ],
          comments=<Comments @1:1 ?children=[
            <LineComment @1:1 value='// hello'>
          ]>>
        ]>
        """,
    ), (
        'if_else_block',
        """
         /* blah */
        if (true) {
          var x = 100;
        } else
         /* foobar */
        {
          var y = 200;
        }
        """,
        """
        <Program @2:1 ?children=[
          <If @2:1 alternative=<Block @6:1 ?children=[
              <VarStatement @7:3 ?children=[
                <VarDecl @7:7 identifier=<Identifier @7:7 value='y'>,
                  initializer=<Number @7:11 value='200'>>
              ]>
            ],
            comments=<Comments @5:2 ?children=[
              <BlockComment @5:2 value='/* foobar */'>
            ]>>,

          comments=<Comments @1:1 ?children=[
            <BlockComment @1:1 value='/* blah */'>
          ]>,
          consequent=<Block @2:11 ?children=[
            <VarStatement @3:3 ?children=[
              <VarDecl @3:7 identifier=<Identifier @3:7 value='x'>,
                initializer=<Number @3:11 value='100'>>
              ]>
            ]>,
          predicate=<Boolean @2:5 value='true'>>
        ]>
        """,
    ), (
        'slash_as_regex_after_function',
        """
        if (0){}/*asdf*//a/
        """,
        r"""
        <Program @1:1 ?children=[
          <If @1:1 alternative=None, consequent=<Block @1:7 >,
            predicate=<Number @1:5 value='0'>>,
          <ExprStatement @1:17 expr=<Regex @1:17 value='/a/'>>
        ]>
        """,
    )]))
