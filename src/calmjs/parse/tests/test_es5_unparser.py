# -*- coding: utf-8 -*-
import unittest
import textwrap

from calmjs.parse import asttypes
from calmjs.parse.ruletypes import Space
from calmjs.parse.ruletypes import Text
from calmjs.parse import layout
from calmjs.parse.parsers.es5 import parse
from calmjs.parse.visitors.generic import ConditionalVisitor

from calmjs.parse.unparsers.base import default_layout_handlers
from calmjs.parse.unparsers.base import minimum_layout_handlers
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.unparsers.es5 import definitions
from calmjs.parse.unparsers.es5 import pretty_print

from calmjs.parse.testing.util import build_equality_testcase


class BaseVisitorTestCase(unittest.TestCase):
    # Many of these tests are here are for showing individual fixes that
    # were done to other classes in order to properly support the source
    # map feature.

    def test_empty_program(self):
        visitor = Unparser()
        ast = parse('')
        self.assertEqual(list(visitor(ast)), [
        ])

    def test_basic_integer(self):
        visitor = Unparser()
        ast = parse('0;')
        self.assertEqual(list(visitor(ast)), [
            ('0', 1, 1, None),
            (';', 1, 2, None),
            ('\n', 0, 0, None),
        ])

    def test_basic_var_space_standard(self):
        visitor = Unparser()
        ast = parse('var x = 0;')
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), (' ', 0, 0, None), ('x', 1, 5, None),
            (' ', 0, 0, None), ('=', 1, 7, None), (' ', 0, 0, None),
            ('0', 1, 9, None), (';', 1, 10, None),
            ('\n', 0, 0, None),
        ])

    def test_basic_var_space_drop(self):
        visitor = Unparser(layout_handlers={
            Space: layout.layout_handler_space_drop,
        })
        ast = parse('var x = 0;\nvar y = 0;')
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), (' ', None, None, None), ('x', 1, 5, None),
            (' ', None, None, None), ('=', 1, 7, None),
            (' ', None, None, None), ('0', 1, 9, None), (';', 1, 10, None),
            ('\n', 0, 0, None),
            ('var', 2, 1, None), (' ', None, None, None), ('y', 2, 5, None),
            (' ', None, None, None), ('=', 2, 7, None),
            (' ', None, None, None), ('0', 2, 9, None), (';', 2, 10, None),
            ('\n', 0, 0, None),
        ])

    def test_force_handler_drop(self):
        visitor = Unparser()
        ast = parse('var x = 0;')
        visitor.layout_handlers.clear()
        # if there are no layout handlers, the layout nodes will just
        # simply be skipped - not very useful as note that there is now
        # no separation between `var` and `x`.
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), ('x', 1, 5, None), ('=', 1, 7, None),
            ('0', 1, 9, None), (';', 1, 10, None),
        ])

    def test_simple_identifier(self):
        visitor = Unparser()
        ast = parse('this;')
        self.assertEqual(list(visitor(ast)), [
            ('this', 1, 1, None), (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_simple_identifier_unmapped(self):
        # if the definition contains unmapped entries
        new_definitions = {}
        new_definitions.update(definitions)
        new_definitions['This'] = (Text(value='this', pos=None),)
        visitor = Unparser(definitions=new_definitions)
        ast = parse('this;')
        self.assertEqual(list(visitor(ast)), [
            ('this', None, None, None), (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_empty_object(self):
        visitor = Unparser()
        ast = parse('thing = {};')
        self.assertEqual(list(visitor(ast)), [
            ('thing', 1, 1, None), (' ', 0, 0, None), ('=', 1, 7, None),
            (' ', 0, 0, None), ('{', 1, 9, None), ('}', 1, 10, None),
            (';', 1, 11, None), ('\n', 0, 0, None),
        ])

    def test_simple_function_declare(self):
        visitor = Unparser()
        ast = parse('function(){};')
        self.assertEqual(list(visitor(ast)), [
            ('function', 1, 1, None),
            ('(', 1, 9, None), (')', 1, 10, None), (' ', 0, 0, None),
            ('{', 1, 11, None), ('\n', 0, 0, None), ('}', 1, 12, None),
            (';', 1, 13, None), ('\n', 0, 0, None),
        ])

    def test_simple_function_invoke(self):
        visitor = Unparser()
        ast = parse('foo();')
        self.assertEqual(list(visitor(ast)), [
            ('foo', 1, 1, None), ('(', 1, 4, None), (')', 1, 5, None),
            (';', 1, 6, None), ('\n', 0, 0, None),
        ])

    def test_new_new(self):
        visitor = Unparser()
        ast = parse('new new T();')
        self.assertEqual(list(visitor(ast)), [
            ('new', 1, 1, None), (' ', 0, 0, None),
            ('new', 1, 5, None), (' ', 0, 0, None),
            ('T', 1, 9, None), ('(', 1, 10, None), (')', 1, 11, None),
            (';', 1, 12, None), ('\n', 0, 0, None),
        ])

    def test_getter(self):
        visitor = Unparser()
        ast = parse('x = {get p() {}};')
        self.assertEqual(list(visitor(ast)), [
            ('x', 1, 1, None), (' ', 0, 0, None), ('=', 1, 3, None),
            (' ', 0, 0, None), ('{', 1, 5, None), ('\n', 0, 0, None),
            ('get', 1, 6, None), (' ', 0, 0, None), ('p', 1, 10, None),
            ('(', 1, 11, None), (')', 1, 12, None),
            (' ', 0, 0, None), ('{', 1, 14, None), ('\n', 0, 0, None),
            ('}', 1, 15, None), ('\n', 0, 0, None),
            ('}', 1, 16, None), (';', 1, 17, None), ('\n', 0, 0, None),
        ])

    def test_setter(self):
        visitor = Unparser()
        ast = parse('x = {set p(a) {}};')
        self.assertEqual(list(visitor(ast)), [
            ('x', 1, 1, None), (' ', 0, 0, None), ('=', 1, 3, None),
            (' ', 0, 0, None), ('{', 1, 5, None), ('\n', 0, 0, None),
            ('set', 1, 6, None), (' ', 0, 0, None), ('p', 1, 10, None),
            ('(', 1, 11, None), ('a', 1, 12, None), (')', 1, 13, None),
            (' ', 0, 0, None), ('{', 1, 15, None), ('\n', 0, 0, None),
            ('}', 1, 16, None), ('\n', 0, 0, None),
            ('}', 1, 17, None), (';', 1, 18, None), ('\n', 0, 0, None),
        ])

    def test_switch_case_default_case(self):
        visitor = Unparser()
        ast = parse('switch (v) { case true: break; default: case false: }')
        self.assertEqual(list(visitor(ast)), [
            ('switch', 1, 1, None), (' ', 0, 0, None), ('(', 1, 8, None),
            ('v', 1, 9, None), (')', 1, 10, None), (' ', 0, 0, None),
            ('{', 1, 12, None),
            ('\n', 0, 0, None),
            ('case', 1, 14, None), (' ', 0, 0, None), ('true', 1, 19, None),
            (':', 1, 23, None),
            ('\n', 0, 0, None),
            ('break', 1, 25, None), (';', 1, 30, None),
            ('\n', 0, 0, None),
            ('default', 1, 32, None), (':', 1, 39, None),
            ('\n', 0, 0, None),
            ('case', 1, 41, None), (' ', 0, 0, None), ('false', 1, 46, None),
            (':', 1, 51, None),
            ('\n', 0, 0, None),
            ('}', 1, 53, None),
            ('\n', 0, 0, None),
        ])

    def test_elision_0(self):
        # basically empty list
        visitor = Unparser()
        ast = parse('[];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None), (']', 1, 2, None),
            (';', 1, 3, None), ('\n', 0, 0, None),
        ])

    def test_elision_1(self):
        visitor = Unparser()
        ast = parse('[,];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None), (',', 1, 2, None), (']', 1, 3, None),
            (';', 1, 4, None), ('\n', 0, 0, None),
        ])

    def test_elision_2(self):
        visitor = Unparser()
        ast = parse('[,,];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None), (',,', 1, 2, None), (']', 1, 4, None),
            (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_elision_4(self):
        visitor = Unparser()
        ast = parse('[,,,,];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None), (',,,,', 1, 2, None), (']', 1, 6, None),
            (';', 1, 7, None), ('\n', 0, 0, None),
        ])

    def test_elision_v3(self):
        visitor = Unparser()
        ast = parse('[1,,,,];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None), ('1', 1, 2, None), (',', 0, 0, None),
            (',,,', 1, 4, None), (']', 1, 7, None),
            (';', 1, 8, None), ('\n', 0, 0, None),
        ])

    def test_elision_vv3(self):
        visitor = Unparser()
        ast = parse('[1, 2,,,,];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None),
            ('1', 1, 2, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('2', 1, 5, None), (',', 0, 0, None),  # ditto for this
            (',,,', 1, 7, None), (']', 1, 10, None),
            (';', 1, 11, None), ('\n', 0, 0, None),
        ])

    def test_elision_v3v(self):
        visitor = Unparser()
        ast = parse('[1,,,, 1];')
        self.assertEqual(list(visitor(ast)), [
            ('[', 1, 1, None), ('1', 1, 2, None), (',', 0, 0, None),
            (',,,', 1, 4, None),
            (' ', 0, 0, None),
            ('1', 1, 8, None), (']', 1, 9, None),
            (';', 1, 10, None), ('\n', 0, 0, None),
        ])

    def test_if_else_block(self):
        visitor = Unparser()
        ast = parse('if (true) {} else {}')
        self.assertEqual([tuple(t) for t in (visitor(ast))], [
            ('if', 1, 1, None),
            (' ', 0, 0, None),
            ('(', 1, 4, None),
            ('true', 1, 5, None),
            (')', 1, 9, None),
            (' ', 0, 0, None),
            ('{', 1, 11, None),
            ('\n', 0, 0, None),
            ('}', 1, 12, None),
            ('\n', 0, 0, None),
            ('else', 1, 14, None),
            (' ', 0, 0, None),
            ('{', 1, 19, None),
            ('\n', 0, 0, None),
            ('}', 1, 20, None),
            ('\n', 0, 0, None),
        ])


class OtherUsageTestCase(unittest.TestCase):
    """
    Test out other forms of usage that are not part of the standard
    chain of calls, e.g. calls that involve manual creation/modification
    of Nodes within the AST.
    """

    def test_manual_element(self):
        # a form of possible manual replacement call.
        ast = asttypes.ES5Program(children=[
            asttypes.ExprStatement(asttypes.FunctionCall(
                identifier=asttypes.Identifier('foo'),
                args=asttypes.Arguments([asttypes.Identifier('x')]),
            )),
        ])
        visitor = Unparser()
        self.assertEqual([tuple(t) for t in (visitor(ast))], [
            ('foo', None, None, None), ('(', None, None, None),
            ('x', None, None, None), (')', None, None, None),
            (';', None, None, None), ('\n', 0, 0, None),
        ])

    def test_remap_function_call(self):
        # a form of possible manual replacement call.
        cv = ConditionalVisitor()
        src = textwrap.dedent("""
        (function(foo, bar, arg1, arg2) {
            foo(arg1);
            bar(arg2);
        })(foo, bar, arg1, arg2);
        """).strip()
        ast = parse(src)
        block = cv.extract(ast, lambda n: isinstance(n, asttypes.FuncExpr))

        for stmt in block.elements:
            fc = stmt.expr
            stmt.expr = asttypes.FunctionCall(
                args=fc.args, identifier=asttypes.DotAccessor(
                    node=asttypes.Identifier(value='window'),
                    identifier=fc.identifier))

        # Now try to render.
        visitor = Unparser()
        self.assertEqual([tuple(t) for t in (visitor(ast))], [
            ('(', 1, 1, None),
            ('function', 1, 2, None),
            ('(', 1, 10, None),
            ('foo', 1, 11, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('bar', 1, 16, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('arg1', 1, 21, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('arg2', 1, 27, None), (')', 1, 31, None),
            (' ', 0, 0, None),
            ('{', 1, 33, None),
            ('\n', 0, 0, None),
            # injected elements should have None for lineno/colno
            ('window', None, None, None), ('.', None, None, None),
            ('foo', 2, 5, None),
            ('(', 2, 8, None), ('arg1', 2, 9, None), (')', 2, 13, None),
            (';', 2, 14, None),
            ('\n', 0, 0, None),
            ('window', None, None, None), ('.', None, None, None),
            ('bar', 3, 5, None),
            ('(', 3, 8, None), ('arg2', 3, 9, None), (')', 3, 13, None),
            (';', 3, 14, None),
            ('\n', 0, 0, None),
            ('}', 4, 1, None),
            (')', 4, 2, None),
            ('(', 4, 3, None), ('foo', 4, 4, None), (',', 0, 0, None),
            (' ', 0, 0, None), ('bar', 4, 9, None), (',', 0, 0, None),
            (' ', 0, 0, None), ('arg1', 4, 14, None), (',', 0, 0, None),
            (' ', 0, 0, None), ('arg2', 4, 20, None),
            (')', 4, 24, None), (';', 4, 25, None), ('\n', 0, 0, None),
        ])

    def test_pretty_print(self):
        # Simple test of the pretty_print function
        src = textwrap.dedent("""
        (function(foo, bar, arg1, arg2) {
          foo(arg1);
          bar(arg2);
        })(foo, bar, arg1, arg2);
        """).lstrip()
        self.assertEqual(pretty_print(parse(src)), src)

    def test_pretty_print_custom_indent(self):
        # Simple test of the pretty_print function
        src = textwrap.dedent("""
        (function(foo, bar, arg1, arg2) {
            foo(arg1);
            bar(arg2);
        })(foo, bar, arg1, arg2);
        """).lstrip()
        self.assertEqual(pretty_print(parse(src), indent_str='    '), src)


def parse_to_sourcemap_tokens_pretty(text):
    return list(Unparser(layouts=(
        default_layout_handlers,
        layout.indentation(),
    ))(parse(text)))


def parse_to_sourcemap_tokens_min(text):
    return list(Unparser(layouts=(
        minimum_layout_handlers,
    ))(parse(text)))


ParsedNodeTypeSrcmapTokenPPTestCase = build_equality_testcase(
    'ParsedNodeTypeSrcmapTokenPPTestCase', parse_to_sourcemap_tokens_pretty, ((
        label,
        textwrap.dedent(argument).strip(),
        result,
    ) for label, argument, result in [(
        'simple',
        """
        0;
        """, [
            ('0', 1, 1, None),
            (';', 1, 2, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'block',
        """
        {
          var a = 5;
        }
        """, [
            ('{', 1, 1, None),
            ('\n', 0, 0, None),
            ('  ', None, None, None),
            ('var', 2, 3, None), (' ', 0, 0, None), ('a', 2, 7, None),
            (' ', 0, 0, None), ('=', 2, 9, None), (' ', 0, 0, None),
            ('5', 2, 11, None), (';', 2, 12, None),
            ('\n', 0, 0, None),
            ('}', 3, 1, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'variable_statement',
        """
        var a;
        var b;
        var a, b = 3;
        var a = 1, b;
        var a = 5, b = 7;
        """, [
            ('var', 1, 1, None), (' ', 0, 0, None), ('a', 1, 5, None),
            (';', 1, 6, None),
            ('\n', 0, 0, None),
            ('var', 2, 1, None), (' ', 0, 0, None), ('b', 2, 5, None),
            (';', 2, 6, None),
            ('\n', 0, 0, None),
            ('var', 3, 1, None), (' ', 0, 0, None), ('a', 3, 5, None),
            (',', 0, 0, None), (' ', 0, 0, None),
            ('b', 3, 8, None), (' ', 0, 0, None), ('=', 3, 10, None),
            (' ', 0, 0, None), ('3', 3, 12, None), (';', 3, 13, None),
            ('\n', 0, 0, None),
            ('var', 4, 1, None), (' ', 0, 0, None), ('a', 4, 5, None),
            (' ', 0, 0, None), ('=', 4, 7, None), (' ', 0, 0, None),
            ('1', 4, 9, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('b', 4, 12, None), (';', 4, 13, None),
            ('\n', 0, 0, None),
            ('var', 5, 1, None), (' ', 0, 0, None), ('a', 5, 5, None),
            (' ', 0, 0, None), ('=', 5, 7, None), (' ', 0, 0, None),
            ('5', 5, 9, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('b', 5, 12, None), (' ', 0, 0, None), ('=', 5, 14, None),
            (' ', 0, 0, None), ('7', 5, 16, None), (';', 5, 17, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'empty_statement',
        """
        ;
        ;
        ;
        """,
        [
            (';', 1, 1, None),
            ('\n', 0, 0, None),
            (';', 2, 1, None),
            ('\n', 0, 0, None),
            (';', 3, 1, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'function_call_0',
        """
        test();
        """,
        [
            # TODO have asttypes call manual position settings
            ('test', 1, 1, None), ('(', 1, 5, None), (')', 1, 6, None),
            (';', 1, 7, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'function_call_1',
        """
        test(1);
        """,
        [
            ('test', 1, 1, None), ('(', 1, 5, None), ('1', 1, 6, None),
            (')', 1, 7, None),
            (';', 1, 8, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'function_call_2',
        """
        test(1, 2);
        """,
        [
            ('test', 1, 1, None), ('(', 1, 5, None),
            ('1', 1, 6, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('2', 1, 9, None),
            (')', 1, 10, None),
            (';', 1, 11, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'operator_1',
        """
        i = 1 + 1;
        """,
        [
            ('i', 1, 1, None),
            (' ', 0, 0, None),
            ('=', 1, 3, None),
            (' ', 0, 0, None),
            ('1', 1, 5, None),
            (' ', 0, 0, None),
            ('+', 1, 7, None),
            (' ', 0, 0, None),
            ('1', 1, 9, None),
            (';', 1, 10, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'unary_op',
        """
        !true;
        !1;
        delete a;
        delete(a);
        ++a;
        a++;
        """,
        [
            ('!', 1, 1, None),
            ('true', 1, 2, None),
            (';', 1, 6, None),
            ('\n', 0, 0, None),
            ('!', 2, 1, None),
            ('1', 2, 2, None),
            (';', 2, 3, None),
            ('\n', 0, 0, None),
            ('delete', 3, 1, None),
            (' ', 0, 0, None),
            ('a', 3, 8, None),
            (';', 3, 9, None),
            ('\n', 0, 0, None),
            ('delete', 4, 1, None),
            ('(', 4, 7, None),
            ('a', 4, 8, None),
            (')', 4, 9, None),
            (';', 4, 10, None),
            ('\n', 0, 0, None),
            ('++', 5, 1, None),
            ('a', 5, 3, None),
            (';', 5, 4, None),
            ('\n', 0, 0, None),
            ('a', 6, 1, None),
            ('++', 6, 2, None),
            (';', 6, 4, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'object',
        """
        var obj = {
            x: 1,
            y: 2,
        }
        """,
        [
            ('var', 1, 1, None),
            (' ', 0, 0, None),
            ('obj', 1, 5, None),
            (' ', 0, 0, None),
            ('=', 1, 9, None),
            (' ', 0, 0, None),
            ('{', 1, 11, None),
            ('\n', 0, 0, None),
            ('  ', None, None, None),
            ('x', 2, 5, None),
            (':', 2, 6, None),
            (' ', 0, 0, None),
            ('1', 2, 8, None),
            (',', 3, 9, None),
            ('\n', 0, 0, None),
            ('  ', None, None, None),
            ('y', 3, 5, None),
            (':', 3, 6, None),
            (' ', 0, 0, None),
            ('2', 3, 8, None),
            ('\n', 0, 0, None),
            ('}', 4, 1, None),
            (';', 0, 0, None),
            ('\n', 0, 0, None),
        ],
    ), (
        'binop_prefixop',
        """
        var a = i+ --i;
        var b = i+ ++i;
        var c = i+ -i;
        """, [
            ('var', 1, 1, None), (' ', 0, 0, None), ('a', 1, 5, None),
            (' ', 0, 0, None), ('=', 1, 7, None), (' ', 0, 0, None),
            ('i', 1, 9, None), (' ', 0, 0, None), ('+', 1, 10, None),
            (' ', 0, 0, None), ('--', 1, 12, None), ('i', 1, 14, None),
            (';', 1, 15, None),
            ('\n', 0, 0, None),
            ('var', 2, 1, None), (' ', 0, 0, None), ('b', 2, 5, None),
            (' ', 0, 0, None), ('=', 2, 7, None), (' ', 0, 0, None),
            ('i', 2, 9, None), (' ', 0, 0, None), ('+', 2, 10, None),
            (' ', 0, 0, None), ('++', 2, 12, None), ('i', 2, 14, None),
            (';', 2, 15, None),
            ('\n', 0, 0, None),
            ('var', 3, 1, None), (' ', 0, 0, None), ('c', 3, 5, None),
            (' ', 0, 0, None), ('=', 3, 7, None), (' ', 0, 0, None),
            ('i', 3, 9, None), (' ', 0, 0, None), ('+', 3, 10, None),
            (' ', 0, 0, None), ('-', 3, 12, None), ('i', 3, 13, None),
            (';', 3, 14, None),
            ('\n', 0, 0, None),
        ],
    )])
)


ParsedToMinimumTestcase = build_equality_testcase(
    'ParsedToMinimumTestcase', parse_to_sourcemap_tokens_min, ((
        label,
        textwrap.dedent(argument).strip(),
        result,
    ) for label, argument, result in [(
        'simple',
        """
        0;
        """, [
            ('0', 1, 1, None),
            (';', 1, 2, None),
        ],
    ), (
        'block',
        """
        {
          var a = 5;
        }
        """, [
            ('{', 1, 1, None),
            ('var', 2, 3, None), (' ', 0, 0, None), ('a', 2, 7, None),
            ('=', 2, 9, None), ('5', 2, 11, None), (';', 2, 12, None),
            ('}', 3, 1, None),
        ],
    ), (
        'variable_statement',
        """
        var a;
        var b;
        var a, b = 3;
        var a = 1, b;
        var a = 5, b = 7;
        """, [
            ('var', 1, 1, None), (' ', 0, 0, None), ('a', 1, 5, None),
            (';', 1, 6, None),
            ('var', 2, 1, None), (' ', 0, 0, None), ('b', 2, 5, None),
            (';', 2, 6, None),
            ('var', 3, 1, None), (' ', 0, 0, None), ('a', 3, 5, None),
            (',', 0, 0, None),
            ('b', 3, 8, None), ('=', 3, 10, None), ('3', 3, 12, None),
            (';', 3, 13, None),
            ('var', 4, 1, None), (' ', 0, 0, None), ('a', 4, 5, None),
            ('=', 4, 7, None), ('1', 4, 9, None), (',', 0, 0, None),
            ('b', 4, 12, None), (';', 4, 13, None),
            ('var', 5, 1, None), (' ', 0, 0, None), ('a', 5, 5, None),
            ('=', 5, 7, None), ('5', 5, 9, None), (',', 0, 0, None),
            ('b', 5, 12, None), ('=', 5, 14, None), ('7', 5, 16, None),
            (';', 5, 17, None),
        ],
    ), (
        'empty_statement',
        """
        ;
        ;
        ;
        """,
        [
            (';', 1, 1, None),
            (';', 2, 1, None),
            (';', 3, 1, None),
        ],
    ), (
        'function_call_0',
        """
        test();
        """,
        [
            # TODO have asttypes call manual position settings
            ('test', 1, 1, None), ('(', 1, 5, None), (')', 1, 6, None),
            (';', 1, 7, None),
        ],
    ), (
        'function_call_1',
        """
        test(1);
        """,
        [
            ('test', 1, 1, None), ('(', 1, 5, None), ('1', 1, 6, None),
            (')', 1, 7, None),
            (';', 1, 8, None),
        ],
    ), (
        'function_call_2',
        """
        test(1, 2);
        """,
        [
            ('test', 1, 1, None), ('(', 1, 5, None),
            ('1', 1, 6, None), (',', 0, 0, None),
            ('2', 1, 9, None),
            (')', 1, 10, None),
            (';', 1, 11, None),
        ],
    ), (
        'operator_1',
        """
        i = 1 + 1;
        """,
        [
            ('i', 1, 1, None),
            ('=', 1, 3, None),
            ('1', 1, 5, None),
            ('+', 1, 7, None),
            ('1', 1, 9, None),
            (';', 1, 10, None),
        ],
    ), (
        'unary_op',
        """
        !true;
        !1;
        delete a;
        delete(a);
        ++a;
        a++;
        """,
        [
            ('!', 1, 1, None),
            ('true', 1, 2, None),
            (';', 1, 6, None),
            ('!', 2, 1, None),
            ('1', 2, 2, None),
            (';', 2, 3, None),
            ('delete', 3, 1, None),
            (' ', 0, 0, None),
            ('a', 3, 8, None),
            (';', 3, 9, None),
            ('delete', 4, 1, None),
            ('(', 4, 7, None),
            ('a', 4, 8, None),
            (')', 4, 9, None),
            (';', 4, 10, None),
            ('++', 5, 1, None),
            ('a', 5, 3, None),
            (';', 5, 4, None),
            ('a', 6, 1, None),
            ('++', 6, 2, None),
            (';', 6, 4, None),
        ],
    ), (
        'object',
        """
        var obj = {
            x: 1,
            y: 2,
        }
        """,
        [
            ('var', 1, 1, None),
            (' ', 0, 0, None),
            ('obj', 1, 5, None),
            ('=', 1, 9, None),
            ('{', 1, 11, None),
            ('x', 2, 5, None),
            (':', 2, 6, None),
            ('1', 2, 8, None),
            (',', 3, 9, None),
            ('y', 3, 5, None),
            (':', 3, 6, None),
            ('2', 3, 8, None),
            ('}', 4, 1, None),
            (';', 0, 0, None),
        ],
    ), (
        'binop_prefixop',
        """
        var a = i+ --i;
        var b = i+ ++i;
        var c = i+ -i;
        """, [
            ('var', 1, 1, None), (' ', 0, 0, None), ('a', 1, 5, None),
            ('=', 1, 7, None),
            ('i', 1, 9, None), ('+', 1, 10, None),
            ('--', 1, 12, None), ('i', 1, 14, None),
            (';', 1, 15, None),
            ('var', 2, 1, None), (' ', 0, 0, None), ('b', 2, 5, None),
            ('=', 2, 7, None),
            ('i', 2, 9, None), ('+', 2, 10, None),
            (' ', 0, 0, None), ('++', 2, 12, None), ('i', 2, 14, None),
            (';', 2, 15, None),
            ('var', 3, 1, None), (' ', 0, 0, None), ('c', 3, 5, None),
            ('=', 3, 7, None),
            ('i', 3, 9, None), ('+', 3, 10, None),
            ('-', 3, 12, None), ('i', 3, 13, None),
            (';', 3, 14, None),
        ],
    )])
)


# TODO use the finalized shorthand invocation to do this; for now show
# that the identity source code can be correctly regenerated.

def parse_to_prettyprint(text):
    return ''.join(c[0] for c in parse_to_sourcemap_tokens_pretty(text))


ES5IdentityTestCase = build_equality_testcase(
    'ES5IdentityTestCase', parse_to_prettyprint, ((
        label, value, value,
    ) for label, value in ((
        label,
        # using lstrip as the pretty printer produces a trailing newline
        textwrap.dedent(value).lstrip(),
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
        """
        if (true) var x = 100;
        """,
    ), (
        'if_empty',
        """
        if (true);
        """,
    ), (
        'if_else_empty',
        """
        if (true);
        else;
        """,
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
        """
        if (true) if (true) var x = 100;
        else var y = 200;
        """,
    ), (
        'if_else_block',
        """
        if (true) {
          var x = 100;
        }
        else {
          var y = 200;
        }
        """,
    ), (
        'if_else_if_else_block_all_empty',
        """
        if (true) {
        }
        else if (null) {
        }
        else {
        }
        """,
    ), (
        'if_else_if_else_block_nested',
        """
        if (true) {
        }
        else if (null) {
          if (true) {
          }
          else if (null) {
          }
          else {
          }
        }
        else {
        }
        """,
    ), (
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
        # retain the semicolon in the initializer part of a 'for' statement
        'iteration_conditional_initializer',
        """
        for (Q || (Q = []); d < b;) {
          d = 1;
        }
        """,
    ), (
        'iteration_new_object',
        """
        for (new Foo(); d < b;) {
          d = 1;
        }
        """,
    ), (
        'iteration_ternary_initializer',
        """
        for (2 >> (foo ? 32 : 43) && 54; 21;) {
          a = c;
        }
        """,
    ), (
        'iteration_regex_initializer',
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
        'while_empty',
        """
        while (false);
        """,
    ), (

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
        'while_loop_break',
        """
        while (true) {
          break;
          s = 'I am not reachable';
        }
        """,
    ), (
        'while_loop_break_label',
        """
        while (true) {
          break label1;
          s = 'I am not reachable';
        }
        """,
    ), (
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
        'with_statement',
        """
        with (x) {
          var y = x * 2;
        }
        """,
    ), (
        'labelled_statement',
        """
        label: while (true) {
          x *= 3;
        }
        """,

    ), (
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

    ), (
        'switch_statement_empty',
        """
        switch (a) {
          default:
          case 1:
          case 2:
        }
        """,

    ), (
        'throw_statement',
        """
        throw 'exc';
        """,

    ), (
        'debugger_statement',
        """
        debugger;
        """,

    ), (
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
        'try_catch_statement',
        """
        try {
          x = 3;
        }
        catch (exc) {
          x = exc;
        }
        """,

    ), (
        'try_finally_statement',
        """
        try {
          x = 3;
        }
        finally {
          x = null;
        }
        """,

    ), (
        'try_catch_finally_statement',
        """
        try {
          x = 5;
        }
        catch (exc) {
          x = exc;
        }
        finally {
          y = null;
        }
        """,

    ), (
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
        'function_call',
        """
        foo();
        """,
    ), (
        'function_call_argument',
        """
        foo(x, 7);
        """,
    ), (
        'function_call_access_element',
        """
        foo()[10];
        """,
    ), (
        'function_call_access_attribute',
        """
        foo().foo;
        """,
    ), (
        'new_keyword',
        """
        var foo = new Foo();
        """,
    ), (
        # dot accessor
        'new_keyword_dot_accessor',
        """
        var bar = new Foo.Bar();
        """,

    ), (
        # bracket accessor
        'new_keyword_bracket_accessor',
        """
        var bar = new Foo.Bar()[7];
        """,

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
        var obj = {};
        """,
    ), (
        # array
        'array_create_access',
        """
        var a = [1, 2, 3, 4, 5];
        var res = a[3];
        """,
    ), (
        # elision
        'elision_1',
        """
        var a = [,,,];
        """,
    ), (
        'elision_2',
        """
        var a = [1,,, 4];
        """,
    ), (
        'elision_3',
        """
        var a = [1,, 3,, 5];
        """,

    ), (
        'function_definition',
        """
        String.prototype.foo = function(data) {
          var tmpl = this.toString();
          return tmpl.replace(/{{\s*(.*?)\s*}}/g, function(a, b) {
            var node = data;
            if (true) {
              var value = true;
            }
            else {
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
        'parentheses_not_removed',
        r"""
        Expr.match[type].source + (/(?![^\[]*\])(?![^\(]*\))/.source);
        """,

    ), (
        'comparison',
        """
        (options = arguments[i]) != null;
        """,

    ), (
        'regex_test',
        """
        return (/h\d/i).test(elem.nodeName);
        """,

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
        """
        return !(match === true || elem.getAttribute("classid") !== match);
        """,

    ), (
        'ternary_dot_accessor',
        """
        var el = (elem ? elem.ownerDocument || elem : 0).documentElement;
        """,

    ), (
        'typeof',
        """
        typeof second.length === "number";
        """,

    ), (
        'prepostfix',
        """
        i++;
        i--;
        ++i;
        --i;
        !i;
        function() {
          i++;
          i--;
          ++i;
          --i;
          !i;
        };
        """,

    ), (
        'shift_ops',
        """
        x << y;
        y >> x;
        function() {
          x << y;
          y >> x;
        };
        """,

    ), (
        'mul_ops',
        """
        x * y;
        y / x;
        x % z;
        function() {
          x * y;
          y / x;
          x % z;
        };
        """,

    ), (
        'various_ops',
        """
        5 + 7 - 20 * 10;
        ++x;
        --x;
        x++;
        x--;
        x = 17 /= 3;
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
        1, 2;
        """,
    ), (
        'regex_isolated',
        """
        s = mot ? z : /x:3;x<5;y</g / i;
        """,
    ), (
        # function call in FOR init
        'function_call_in_for_init',
        """
        for (o(); i < 3; i++) {
        }
        """,

    ), (
        # function call in FOR init
        'function_call_various',
        """
        a();
        a()();
        d()['test'];
        d().test;
        var i = a();
        var i = a()();
        var i = d()['test'];
        var i = d().test;
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
    ), (
        'var_function_named',
        """
        var x = function y() {
        };
        """,
    ), (
        'new_expr_lhs',
        """
        new T();
        new T().derp;
        """,
    ), (
        'new_new_expr',
        # var T = function(){ return function (){} }
        """
        new new T();
        var x = new new T();
        """,
    ), (
        # delete
        'delete_keyword',
        """
        var obj = {
          foo: 1
        };
        delete obj.foo;
        """,
    ), (
        'object_various',
        """
        var obj = {
          foo: 1,
          set bar(x) {
            this._bar = x + 1;
          },
          get bar() {
            return this._bar;
          }
        };
        """,
    ), (
        'void_keyword',
        """
        void 0;
        """,
    ), (
        'instanceof',
        """
        x instanceof y;
        """,
    ), (
        # membership
        'membership_in',
        """
        1 in s;
        """,
    ), (
        'for_various',
        """
        for (;;);
        for (o < (p < q);;);
        for (o == (p == q);;);
        for (o ^ (p ^ q);;);
        for (o | (p | q);;);
        for (o & (p & q);;);
        for (a ? (b ? c : d) : false;;);
        for (var x;;);
        for (var x, y, z;;);
        """,
    ), (
        'forin_various',
        """
        for (f in o < (p < q));
        for (f in o == (p == q));
        for (f in o ^ (p ^ q));
        for (f in o | (p | q));
        for (f in o & (p & q));
        for (f in a ? (b ? c : d) : false);
        for (f in x);
        for (f in x, y, z);
        """,
    ), (
        'forin_initializer_noin',
        """
        for (var x = foo() in (bah())) {
        }
        """,
    ), (
        'dot_reserved_word',
        """
        e.case;
        """,
    ), (
        'dot_reserved_word_nobf',
        """
        for (x = e.case;;);
        """,
    ), (
        'logical_or_expr_nobf',
        """
        (true || true) || (false && false);
        """,
    ), (
        'multiplicative_expr_nobf',
        """
        !0 % 1;
        """,
    ), (
        'function_expr_1',
        """
        function(arg) {
        };
        """,
    ), (
        'octal_slimit_issue_70',
        r"""
        var x = '\071[90m%s';
        """,
    ), (
        'special_array_char_slimit_issue_82',
        r"""
        var x = ['a', '\n'];
        """,
    ), (
        'special_string_slimit_issue_82',
        r"""
        var x = '\n';
        """,
    ), (
        'for_in_without_braces',
        """
        for (index in [1, 2, 3]) index;
        """,
    ), (
        'for_loop_into_regex_slimit_issue_54',
        """
        for (index in [1, 2, 3]) /^salign$/;
        """,
    )]))
)
