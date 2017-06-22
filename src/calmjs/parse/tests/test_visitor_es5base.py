# -*- coding: utf-8 -*-
import unittest
import textwrap

# XXX compat import
from calmjs.parse import _es5_sourcemap_compat as es5
from calmjs.parse.pptypes import Space
from calmjs.parse.pptypes import Text
from calmjs.parse.visitors import es5base
from calmjs.parse.visitors import layout

from calmjs.parse.testing.util import build_equality_testcase


class BaseVisitorTestCase(unittest.TestCase):
    # Many of these tests are here are for showing individual fixes that
    # were done to other classes in order to properly support the source
    # map feature.

    def test_empty_program(self):
        visitor = es5base.BaseVisitor()
        ast = es5('')
        self.assertEqual(list(visitor(ast)), [
        ])

    def test_basic_integer(self):
        visitor = es5base.BaseVisitor()
        ast = es5('0;')
        self.assertEqual(list(visitor(ast)), [
            ('0', 1, 1, None),
            (';', 1, 2, None),
            ('\n', 0, 0, None),
        ])

    def test_basic_var_space_standard(self):
        visitor = es5base.BaseVisitor()
        ast = es5('var x = 0;')
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), (' ', 0, 0, None), ('x', 1, 5, None),
            (' ', 0, 0, None), ('=', 1, 7, None), (' ', 0, 0, None),
            ('0', 1, 9, None), (';', 1, 10, None),
            ('\n', 0, 0, None),
        ])

    def test_basic_var_space_drop(self):
        visitor = es5base.BaseVisitor(layout_handlers={
            Space: layout.layout_handler_space_drop,
        })
        ast = es5('var x = 0;\nvar y = 0;')
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
        visitor = es5base.BaseVisitor()
        ast = es5('var x = 0;')
        visitor.layout_handlers.clear()
        # if there are no layout handlers, the layout nodes will just
        # simply be skipped - not very useful as note that there is now
        # no separation between `var` and `x`.
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), ('x', 1, 5, None), ('=', 1, 7, None),
            ('0', 1, 9, None), (';', 1, 10, None),
        ])

    def test_simple_identifier(self):
        visitor = es5base.BaseVisitor()
        ast = es5('this;')
        self.assertEqual(list(visitor(ast)), [
            ('this', 1, 1, None), (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_simple_identifier_unmapped(self):
        # if the definition contains unmapped entries
        new_definitions = {}
        new_definitions.update(es5base.definitions)
        new_definitions['This'] = (Text(value='this', pos=None),)
        visitor = es5base.BaseVisitor(definitions=new_definitions)
        ast = es5('this;')
        self.assertEqual(list(visitor(ast)), [
            ('this', None, None, None), (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_empty_object(self):
        visitor = es5base.BaseVisitor()
        ast = es5('thing = {};')
        self.assertEqual(list(visitor(ast)), [
            ('thing', 1, 1, None), (' ', 0, 0, None), ('=', 1, 7, None),
            (' ', 0, 0, None), ('{', 1, 9, None), ('}', 1, 10, None),
            (';', 1, 11, None), ('\n', 0, 0, None),
        ])

    def test_simple_function_declare(self):
        visitor = es5base.BaseVisitor()
        ast = es5('function(){};')
        self.assertEqual(list(visitor(ast)), [
            ('function', 1, 1, None), (' ', 0, 0, None),
            ('(', 1, 9, None), (')', 1, 10, None), (' ', 0, 0, None),
            ('{', 1, 11, None), ('\n', 0, 0, None), ('}', 1, 12, None),
            (';', 1, 13, None), ('\n', 0, 0, None),
        ])

    def test_simple_function_invoke(self):
        visitor = es5base.BaseVisitor()
        ast = es5('foo();')
        self.assertEqual(list(visitor(ast)), [
            ('foo', 1, 1, None), ('(', 1, 4, None), (')', 1, 5, None),
            (';', 1, 6, None), ('\n', 0, 0, None),
        ])

    def test_new_new(self):
        visitor = es5base.BaseVisitor()
        ast = es5('new new T();')
        self.assertEqual(list(visitor(ast)), [
            ('new', 1, 1, None), (' ', 0, 0, None),
            ('new', 1, 5, None), (' ', 0, 0, None),
            ('T', 1, 9, None), ('(', 1, 10, None), (')', 1, 11, None),
            (';', 1, 12, None), ('\n', 0, 0, None),
        ])

    def test_getter(self):
        visitor = es5base.BaseVisitor()
        ast = es5('x = {get p() {}};')
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
        visitor = es5base.BaseVisitor()
        ast = es5('x = {set p(a) {}};')
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
        visitor = es5base.BaseVisitor()
        ast = es5('switch (v) { case true: break; default: case false: }')
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
            ('\n', 0, 0, None),  # XXX this is extra
            ('default', 1, 32, None), (':', 1, 39, None),
            ('\n', 0, 0, None),
            ('\n', 0, 0, None),  # XXX this is extra
            ('case', 1, 41, None), (' ', 0, 0, None), ('false', 1, 46, None),
            (':', 1, 51, None),
            ('\n', 0, 0, None),
            ('}', 1, 53, None),
            ('\n', 0, 0, None),
        ])


def parse_to_sourcemap_tokens_pretty(text):
    return list(es5base.BaseVisitor(layouts=(
        es5base.default_layout_handlers,
        layout.indentation(),
    ))(es5(text)))


def parse_to_sourcemap_tokens_min(text):
    return list(es5base.BaseVisitor(layouts=(
        es5base.minimum_layout_handlers,
    ))(es5(text)))


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
