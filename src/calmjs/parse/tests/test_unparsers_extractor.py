# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import textwrap
import unittest

from calmjs.parse.parsers import es5
from calmjs.parse.unparsers.extractor import Unparser


def parse(src):
    return es5.parse(textwrap.dedent(src).strip())


class ExtractorUnparserTestCase(unittest.TestCase):

    def test_empty_program(self):
        unparser = Unparser()
        ast = parse('')
        self.assertEqual(list(unparser(ast)), [
        ])

    def test_singular_atom(self):
        unparser = Unparser()
        ast = parse('0;')
        self.assertEqual(list(unparser(ast)), [
            [NotImplemented, [0]],
        ])

    def test_singular_assignment_pair(self):
        unparser = Unparser()
        ast = parse('''
        var x = 0;
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['x', 0],
        ])

    def test_inline_double(self):
        unparser = Unparser()
        ast = parse('''
        a = b = 'hello';
        var x = y = 42;
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['a', 'hello'],
            ['b', 'hello'],
            ['x', 42],
            ['y', 42],
        ])

    def test_var_multiple(self):
        unparser = Unparser()
        ast = parse('''
        var x = 69, y = 420;
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['x', 69],
            ['y', 420],
        ])

    def test_var_undefined(self):
        unparser = Unparser()
        ast = parse('''
        var x, y;
        ''')
        # JavaScript `undefined` values are simply casted to None
        self.assertEqual(list(unparser(ast)), [
            ['x', None],
            ['y', None],
        ])

    def test_inline_multiassign(self):
        unparser = Unparser()
        ast = parse('''
        a = b = c = d = 'hello';
        var x = y = z = 42;
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['a', 'hello'],
            ['b', 'hello'],
            ['c', 'hello'],
            ['d', 'hello'],
            ['x', 42],
            ['y', 42],
            ['z', 42],
        ])

    def test_multiple_assignment_pairs(self):
        unparser = Unparser()
        ast = parse('''
        var x = 0;
        var y = 'abc';
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['x', 0],
            ['y', 'abc'],
        ])

    def test_list_assignment(self):
        unparser = Unparser()
        ast = parse('''
        var a_list = [1, 2, 3, 'foobar', 0];
        var b_list = [];
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['a_list', [1, 2, 3, 'foobar', 0]],
            ['b_list', []],
        ])

    def test_list_in_a_list(self):
        unparser = Unparser()
        ast = parse('''
        var a_list = [1, [2, [3, 'foobar', 0]]];
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['a_list', [1, [2, [3, 'foobar', 0]]]],
        ])

    def test_object_assignment_basic(self):
        unparser = Unparser()
        ast = parse('''
        var obj_a = {
            a: 1,
            'b': 2,
            'c': [1, 2],
        }
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['obj_a', {'a': 1, 'b': 2, 'c': [1, 2]}]
        ])

    def test_object_assignment_getter_setter(self):
        unparser = Unparser()
        ast = parse('''
        var obj_a = {
            get bar() {
                x = 1;
            },
            set bar(x) {
                x = 2;
            },
        }
        ''')
        # Only the final value is returned for now as there is no way to
        # easily disambiguate or compbine the two.
        self.assertEqual(list(unparser(ast)), [
            ['obj_a', {'bar': {'x': 2}}],
        ])

    def test_object_assignment_getter_return(self):
        unparser = Unparser()
        ast = parse('''
        var obj_a = {
            get bar() {
                x = 1;
                return x
            },
        }
        ''')
        # The actual value won't be returned, instead the raw variable
        # identifier will be.
        self.assertEqual(list(unparser(ast)), [
            ['obj_a', {'bar': {'x': 1, 'return': 'x'}}],
        ])

    def test_dot_accessor_assignment(self):
        unparser = Unparser()
        ast = parse('''
        some.attrib.a = 'value'
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['some.attrib.a', 'value']
        ])

    def test_bracket_accessor_assignment(self):
        unparser = Unparser()
        ast = parse('''
        some['attrib']['a'] = 'value'
        some[id]['a'] = 'value'
        ''')
        # Note that the quoted string is dropped to be an identifier
        self.assertEqual(list(unparser(ast)), [
            ['some[attrib][a]', 'value'],
            ['some[id][a]', 'value'],
        ])

    def test_various_special_values(self):
        unparser = Unparser()
        ast = parse('''
        a = true;
        b = false;
        c = null;
        ''')
        self.assertEqual(list(unparser(ast)), [
            ['a', True],
            ['b', False],
            ['c', None],
        ])
