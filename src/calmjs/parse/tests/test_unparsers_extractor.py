# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import textwrap
import unittest

from calmjs.parse.asttypes import (
    Block,
    Case,
    Default,
    DoWhile,
    For,
    ForIn,
    FunctionCall,
    Identifier,
    If,
    Number,
    GetPropAssign,
    SetPropAssign,
    Switch,
    With,
    While,
)
from calmjs.parse.parsers import es5
from calmjs.parse.unparsers.extractor import (
    Assignment,
    AssignmentList,
    ExtractedFragment,
    Unparser,
)


def parse(src):
    return es5.parse(textwrap.dedent(src).strip())


class SupportTestCase(unittest.TestCase):

    def test_repr(self):
        assignment = Assignment(
            ExtractedFragment(1, Number(value=1)),
            ExtractedFragment(1, Number(value=1)),
        )
        self.assertEqual('(1, 1)', repr(assignment))

        assignmentlist = AssignmentList(assignment)
        self.assertEqual('[(1, 1)]', repr(assignmentlist))

    def test_assignment_attributes(self):
        assignment = Assignment(1, 2)
        self.assertEqual(assignment.key, 1)
        self.assertEqual(assignment.value, 2)

        assignment_frag = Assignment(
            ExtractedFragment(1, Number(value=1)),
            ExtractedFragment(2, Number(value=2)),
        )
        self.assertEqual(assignment_frag.key, 1)
        self.assertEqual(assignment_frag.value, 2)

    def test_assignment_list_creation(self):
        assignmentlist = AssignmentList([1, 2])
        self.assertEqual(Assignment(1, 2), assignmentlist[0])
        self.assertEqual(1, len(assignmentlist))
        assignmentlist2 = AssignmentList(assignmentlist)
        self.assertIs(assignmentlist[0], assignmentlist2[0])

        assignmentlist3 = AssignmentList([1, 2, 3])
        self.assertEqual(Assignment(1, [2, 3]), assignmentlist3[0])

        with self.assertRaises(ValueError) as e:
            AssignmentList([1])

        self.assertEqual(
            e.exception.args[0],
            '[1] cannot be converted to an Assignment',
        )

    def test_assignment_list_modify(self):
        assignmentlist = AssignmentList([1, 2], [3, 4])
        assignmentlist[1] = [4, 5]
        self.assertEqual(Assignment(4, 5), assignmentlist[1])
        del assignmentlist[0]
        self.assertEqual(Assignment(4, 5), assignmentlist[0])
        self.assertEqual(1, len(assignmentlist))


class ExtractorUnparserTestCase(unittest.TestCase):

    def test_empty_program(self):
        unparser = Unparser()
        ast = parse('')
        self.assertEqual(dict(unparser(ast)), {})

    def test_empty_statements(self):
        unparser = Unparser()
        ast = parse(";;;")
        self.assertEqual(dict(unparser(ast)), {})

    def test_singular_atom(self):
        unparser = Unparser()
        ast = parse('0;')
        self.assertEqual(dict(unparser(ast)), {
            Number: [0],
        })

    def test_multiple_atoms(self):
        unparser = Unparser()
        ast = parse('{}0;{}1;{}2;')
        self.assertEqual(dict(unparser(ast)), {
            Number: [0, 1, 2],
            Block: [{}, {}, {}],
        })

    def test_singular_assignment_pair(self):
        unparser = Unparser()
        ast = parse('''
        var x = 0;
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'x': 0,
        })

    def test_inline_double(self):
        unparser = Unparser()
        ast = parse('''
        a = b = 'hello';
        var x = y = 42;
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'a': 'hello',
            'b': 'hello',
            'x': 42,
            'y': 42,
        })

    def test_var_multiple(self):
        unparser = Unparser()
        ast = parse('''
        var x = 69, y = 420;
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'x': 69,
            'y': 420,
        })

    def test_var_undefined(self):
        unparser = Unparser()
        ast = parse('''
        var x, y;
        ''')
        # JavaScript `undefined` values are simply casted to None
        self.assertEqual(dict(unparser(ast)), {
            'x': None,
            'y': None,
        })

    def test_inline_multiassign(self):
        unparser = Unparser()
        ast = parse('''
        a = b = c = d = 'hello';
        var x = y = z = 42;
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'a': 'hello',
            'b': 'hello',
            'c': 'hello',
            'd': 'hello',
            'x': 42,
            'y': 42,
            'z': 42,
        })

    def test_multiple_assignment_pairs(self):
        unparser = Unparser()
        ast = parse('''
        var x = 0;
        var y = 'abc';
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'x': 0,
            'y': 'abc',
        })

    def test_list_assignment(self):
        unparser = Unparser()
        ast = parse('''
        var a_list = [1, 2, 3, 'foobar', 0];
        var b_list = [];
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'a_list': [1, 2, 3, 'foobar', 0],
            'b_list': [],
        })

    def test_list_in_a_list(self):
        unparser = Unparser()
        ast = parse('''
        var a_list = [1, [2, [3, 'foobar', 0]]];
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'a_list': [1, [2, [3, 'foobar', 0]]],
        })

    def test_object_assignment_basic(self):
        unparser = Unparser()
        ast = parse('''
        var obj_a = {
            a: 1,
            'b': 2,
            'c': [1, 2],
        }
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'obj_a': {'a': 1, 'b': 2, 'c': [1, 2]}
        })

    def test_object_assignment_getter_setter(self):
        unparser = Unparser()
        ast = parse('''
        var obj_a = {
            foo: 1,
            get bar() {
                x = 1;
                return x;
            },
            set bar(x) {
                x = 2;
                return
            },
        }
        ''')
        # getter and setters are dumped out as an item under the
        # NotImplemented key.
        self.assertEqual(dict(unparser(ast)), {
            'obj_a': {
                'foo': 1,
                GetPropAssign: [
                    ['bar', {'x': 1, 'return': 'x'}],
                ],
                SetPropAssign: [
                    ['bar', {'x': 2}],
                ],
            },
        })

    def test_dot_accessor_assignment(self):
        unparser = Unparser()
        ast = parse('''
        some.attrib.a = 'value'
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'some.attrib.a': 'value'
        })

    def test_bracket_accessor_assignment(self):
        unparser = Unparser()
        ast = parse('''
        some['attrib']['a'] = 'value'
        some[id]['a'] = 'value'
        ''')
        # Note that the quoted string is dropped to be an identifier
        self.assertEqual(dict(unparser(ast)), {
            'some[attrib][a]': 'value',
            'some[id][a]': 'value',
        })

    def test_various_special_values(self):
        unparser = Unparser()
        ast = parse('''
        a = true;
        b = false;
        c = null;
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'a': True,
            'b': False,
            'c': None,
        })

    def test_basic_operator_str(self):
        unparser = Unparser()
        ast = parse("""
        a = 'hello' + ' ' + 'world';
        """)
        self.assertEqual(dict(unparser(ast)), {
            'a': 'hello +   + world',
        })

    def test_ternary_assignment(self):
        unparser = Unparser()
        ast = parse("""
        a = 1 ? '1' : false;
        """)
        self.assertEqual(dict(unparser(ast)), {
            'a': [1, '1', False],
        })

    def test_funcdecl(self):
        unparser = Unparser()
        ast = parse("""
        function a() {
            foo = 1;
        }
        function b() {
            bar = 2;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            'a': [[], {
                'foo': 1,
            }],
            'b': [[], {
                'bar': 2,
            }],
        })

    def test_funcexpr_assignment(self):
        unparser = Unparser()
        ast = parse("""
        a = function a() {
            foo = 1;
        };
        """)
        self.assertEqual(dict(unparser(ast)), {
            'a': [[], {
                'foo': 1,
            }],
        })

    def test_funcexpr_argument_assignment(self):
        unparser = Unparser()
        ast = parse("""
        a = function a(arg1, arg2) {
            foo = 1;
        };
        """)
        self.assertEqual(dict(unparser(ast)), {
            'a': [['arg1', 'arg2'], {
                'foo': 1,
            }]
        })

    def test_functioncall(self):
        unparser = Unparser()
        ast = parse("""
        foo = bar(a, b, d);
        """)
        # The result is due the grouping operator and the nested nature
        # of the anonymous call.
        self.assertEqual(dict(unparser(ast)), {
            'foo': ['bar', ['a', 'b', 'd']],
        })

    def test_new_functioncall(self):
        unparser = Unparser()
        ast = parse("""
        foo = new bar(a, b, d);
        """)
        # The result is due the grouping operator and the nested nature
        # of the anonymous call.
        self.assertEqual(dict(unparser(ast)), {
            'foo': ['bar', ['a', 'b', 'd']],
        })

    def test_funcexpr_anonymous_functioncall(self):
        unparser = Unparser()
        ast = parse("""
        (function () {
            foo = 1;
        })();
        """)
        # The result is due the grouping operator and the nested nature
        # of the anonymous call.
        self.assertEqual(dict(unparser(ast)), {
            FunctionCall: [[[[], {'foo': 1}], []]]
        })

    def test_label(self):
        unparser = Unparser()
        ast = parse("""
        var foo;
        labela:
            foo = 'bar';
        bar = 'baz';
        """)
        self.assertEqual(dict(unparser(ast)), {
            'foo': None,
            'labela': {'foo': 'bar'},
            'bar': 'baz',
        })

    def test_for_basic(self):
        unparser = Unparser()
        ast = parse("""
        a = 0
        for (; a < 1;) {
          a = a + 1
        }
        for (;;) {
        }
        for (i = 0, j = 10; i < j && j < 15; i++, j++) {
          x = i * j;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            For: [
                ['a < 1', {Block: [{'a': 'a + 1'}]}],
                [{Block: [{}]}],
                ['i < j && j < 15', 'i', 'j', {Block: [{'x': 'i * j'}]}],
            ],
            'a': 0,
            'i': 0,
            'j': 10,
        })

    def test_for_var(self):
        unparser = Unparser()
        # this includes Comma, PostfixExpr, UnaryExpr
        ast = parse("""
        for (var i = 0, j = 10; i < j && j < 15; i++, ++j) {
          x = i * j;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            For: [
                ['i < j && j < 15', 'i', 'j', {Block: [{'x': 'i * j'}]}],
            ],
            'i': 0,
            'j': 10,
        })

    def test_for_in_various(self):
        unparser = Unparser()
        ast = parse("""
        for (index in [1,2,3]) index
        for (index in [1,2,3]) {
            i = index;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            ForIn: [
                ['index', [1, 2, 3], {Identifier: ['index']}],
                ['index', [1, 2, 3], {Block: [{'i': 'index'}]}],
            ],
        })

    def test_if_statement_various(self):
        unparser = Unparser()
        ast = parse("""
        if (true)
            var x = 100;
        else
            var x = 200;

        if (x < 100) {
            y = 1;
            z = 2;
        }
        else if (x < 200) {
            x = 2;
            y = 4;
        }
        else {
            x = 0;
            y = 0;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            If: [
                [True, {'x': 100}, {'x': 200}],
                ['x < 100', {
                    Block: [{'y': 1, 'z': 2}],
                }, {
                    If: [[
                        'x < 200',
                        {Block: [{'x': 2, 'y': 4}]},
                        {Block: [{'x': 0, 'y': 0}]},
                    ]]
                }]
            ]
        })

    def test_while(self):
        unparser = Unparser()
        ast = parse("""
        while (false) {
          x = 1;
          y = 2;
        }

        while (true) {
          x = 2;
          y = 4;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            While: [
                [False, {Block: [{
                    'x': 1,
                    'y': 2,
                }]}],
                [True, {Block: [{
                    'x': 2,
                    'y': 4,
                }]}],
            ],
        })

    def test_do_while(self):
        unparser = Unparser()
        ast = parse("""
        do {
          x = 1;
          y = 2;
        } while (false);

        do {
          x = 2;
          y = 4;
        } while (true);
        """)
        self.assertEqual(dict(unparser(ast)), {
            DoWhile: [
                [{Block: [{
                    'x': 1,
                    'y': 2,
                }]}, False],
                [{Block: [{
                    'x': 2,
                    'y': 4,
                }]}, True],
            ],
        })

    def test_with_statements(self):
        unparser = Unparser()
        ast = parse("""
        with (x) {
          x = x * 2;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            With: [
                ['x', {Block: [{
                    'x': 'x * 2',
                }]}],
            ],
        })

    def test_switch_case_blocks(self):
        unparser = Unparser()
        ast = parse("""
        switch (result) {
          case 'good':
            gooder = 1;
          case 'poor':
            poorer = 2;
            break;
          default:
            unexpected = 3;
          case 'errored':
            error = 4;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            Switch: [[
                'result', {
                    Case: [
                        ['good', {'gooder': 1}],
                        ['poor', {'poorer': 2}],
                        ['errored', {'error': 4}],
                    ],
                    Default: [
                        [{'unexpected': 3}],
                    ],
                },
            ]],
        })
