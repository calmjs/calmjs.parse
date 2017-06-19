# -*- coding: utf-8 -*-
import unittest
import textwrap

# XXX compat import
from calmjs.parse import _es5_sourcemap_compat as es5
from calmjs.parse.visitors import es5base

from calmjs.parse.testing.util import build_equality_testcase


class BaseTypesTestCase(unittest.TestCase):
    """
    Test out the core base types
    """

    def test_token(self):
        token = es5base.Token()
        self.assertTrue(callable(token))
        with self.assertRaises(NotImplementedError):
            token(None, None, None)


class BaseVisitorTestCase(unittest.TestCase):

    def test_basic_integer(self):
        visitor = es5base.BaseVisitor()
        ast = es5('0;')
        self.assertEqual(list(visitor(ast)), [
            ('0', 1, 1, None),
            (';', 1, 2, None),
        ])

    def test_basic_var_space_standard(self):
        visitor = es5base.BaseVisitor()
        ast = es5('var x = 0;')
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), (' ', 0, 0, None), ('x', 1, 5, None),
            ('=', 1, 7, None), ('0', 1, 9, None), (';', 1, 10, None),
        ])

    def test_basic_var_space_drop(self):
        visitor = es5base.BaseVisitor(handlers={
            es5base.Space: es5base.node_handler_space_drop
        })
        ast = es5('var x = 0;')
        self.assertEqual(list(visitor(ast)), [
            ('var', 1, 1, None), (' ', None, None, None), ('x', 1, 5, None),
            ('=', 1, 7, None), ('0', 1, 9, None), (';', 1, 10, None),
        ])

    def test_force_handler_drop(self):
        visitor = es5base.BaseVisitor()
        ast = es5('var x = 0;')

        # when the handlers are undefined, this happens:
        visitor.handlers.clear()
        with self.assertRaises(NotImplementedError):
            list(visitor(ast))

    def test_simple_identifier(self):
        visitor = es5base.BaseVisitor()
        ast = es5('this;')
        self.assertEqual(list(visitor(ast)), [
            ('this', 1, 1, None), (';', 1, 5, None),
        ])

    def test_simple_identifier_unmapped(self):
        # if the definition contains unmapped entries
        new_definitions = {}
        new_definitions.update(es5base.definitions)
        new_definitions['This'] = (es5base.Text(value='this', pos=None),)
        visitor = es5base.BaseVisitor(definitions=new_definitions)
        ast = es5('this;')
        self.assertEqual(list(visitor(ast)), [
            ('this', None, None, None), (';', 1, 5, None),
        ])


def parse_to_sourcemap_tokens(text):
    return list(es5base.BaseVisitor()(es5(text)))


ParsedNodeTypeSrcmapCompatTestCase = build_equality_testcase(
    'ParsedNodeTypeSrcmapCompatTestCase', parse_to_sourcemap_tokens, ((
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
            ('\n', 0, 0, None),
            ('var', 2, 3, None), (' ', 0, 0, None), ('a', 2, 7, None),
            ('=', 2, 9, None), ('5', 2, 11, None), (';', 2, 12, None),
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
            ('b', 3, 8, None), ('=', 3, 10, None), ('3', 3, 12, None),
            (';', 3, 13, None),
            ('\n', 0, 0, None),
            ('var', 4, 1, None), (' ', 0, 0, None), ('a', 4, 5, None),
            ('=', 4, 7, None), ('1', 4, 9, None), (',', 0, 0, None),
            (' ', 0, 0, None), ('b', 4, 12, None), (';', 4, 13, None),
            ('\n', 0, 0, None),
            ('var', 5, 1, None), (' ', 0, 0, None), ('a', 5, 5, None),
            ('=', 5, 7, None), ('5', 5, 9, None), (',', 0, 0, None),
            (' ', 0, 0, None), ('b', 5, 12, None), ('=', 5, 14, None),
            ('7', 5, 16, None), (';', 5, 17, None),
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
        ],
    ), (
        'function_call_0',
        """
        test();
        """,
        [
            # TODO have asttypes call manual position settings
            ('test', 1, 1, None), ('(', 0, 0, None), (')', 0, 0, None),
            (';', 1, 7, None),
        ],
    ), (
        'function_call_1',
        """
        test(1);
        """,
        [
            ('test', 1, 1, None), ('(', 0, 0, None), ('1', 1, 6, None),
            (')', 0, 0, None),
            (';', 1, 8, None),
        ],
    ), (
        'function_call_2',
        """
        test(1, 2);
        """,
        [
            ('test', 1, 1, None), ('(', 0, 0, None),
            ('1', 1, 6, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('2', 1, 9, None),
            (')', 0, 0, None),
            (';', 1, 11, None),
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
            (';', 1, 10, None)
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
            ('\n', 0, 0, None),
            ('x', 2, 5, None),
            (' ', 0, 0, None),  # TODO should be optional
            (':', 2, 6, None),
            (' ', 0, 0, None),
            ('1', 2, 8, None),
            (',', 3, 9, None),
            ('\n', 0, 0, None),
            ('y', 3, 5, None),
            (' ', 0, 0, None),
            (':', 3, 6, None),
            (' ', 0, 0, None),
            ('2', 3, 8, None),
            ('\n', 0, 0, None),
            ('}', 4, 1, None),
            (';', 0, 0, None),
        ],
    )])
)
