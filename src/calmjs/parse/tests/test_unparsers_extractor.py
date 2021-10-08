# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import textwrap
import unittest

from calmjs.parse.asttypes import (
    Array,
    Block,
    Boolean,
    Case,
    Catch,
    Default,
    DoWhile,
    Finally,
    For,
    ForIn,
    FunctionCall,
    Identifier,
    If,
    Object,
    Null,
    Number,
    GetPropAssign,
    SetPropAssign,
    String,
    Switch,
    Try,
    UnaryExpr,
    With,
    While,
)
from calmjs.parse.parsers import es5
from calmjs.parse.ruletypes import (
    Attr,
    JoinAttr,
)
from calmjs.parse.unparsers.extractor import (
    Assignment,
    AssignmentList,
    Dispatcher,
    ExtractedFragment,
    FoldedFragment,
    GroupAsBinOp,
    GroupAsBinOpBitwise,
    GroupAsBinOpPlus,
    GroupAsUnaryExpr,
    GroupAsUnaryExprPlus,
    Unparser,
    definitions,
    extractor,
    ast_to_dict,
    logger as extractor_logger,
    to_boolean,
    to_number,
    to_int32,
    to_primitive,
    to_string,
    value_to_str,
)
from calmjs.parse.testing.util import setup_logger


def parse(src):
    return es5.parse(textwrap.dedent(src).strip())


class SupportTestCase(unittest.TestCase):

    def test_assignment_repr(self):
        assignment = Assignment(
            ExtractedFragment(1, Number(value=1), None),
            ExtractedFragment(1, Number(value=1), None),
        )
        self.assertEqual('(1, 1)', repr(assignment))

        assignmentlist = AssignmentList(assignment)
        self.assertEqual('[(1, 1)]', repr(assignmentlist))

    def test_assignment_attributes(self):
        assignment = Assignment(1, 2)
        self.assertEqual(assignment.key, 1)
        self.assertEqual(assignment.value, 2)

        assignment_frag = Assignment(
            ExtractedFragment(1, Number(value=1), None),
            ExtractedFragment(2, Number(value=2), None),
        )
        self.assertEqual(assignment_frag.key, 1)
        self.assertEqual(assignment_frag.value, 2)

    def test_assignment_list_creation(self):
        assignmentlist = AssignmentList([1, 2])
        self.assertEqual(Assignment(1, 2), assignmentlist[0])
        self.assertEqual(1, len(assignmentlist))
        assignmentlist2 = AssignmentList(assignmentlist)
        self.assertIs(assignmentlist[0], assignmentlist2[0])

        with self.assertRaises(ValueError) as e:
            AssignmentList([1, 2, 3])

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

    def test_assignment_list_generic_equality(self):
        assignmentlist = AssignmentList(Assignment(1, 2), Assignment(3, 4))
        self.assertEqual([(1, 2), (3, 4)], assignmentlist)


class TypeConversionTestCase(unittest.TestCase):

    def test_value_to_str(self):
        with self.assertRaises(TypeError):
            value_to_str(object())

    def test_to_primitive_various_lists(self):
        def assertArrayToPrimitive(hint, left, right):
            # local test helper; move out when appropriate.
            self.assertEqual(
                FoldedFragment(left, hint),
                to_primitive(FoldedFragment(right, Array), hint),
            )

        assertArrayToPrimitive(String, '', [])
        assertArrayToPrimitive(String, '1', [1])
        assertArrayToPrimitive(String, '1,2', [1, 2])
        assertArrayToPrimitive(String, '1,2,3', [1, 2, 3])
        assertArrayToPrimitive(
            String, '1,2,3,4,5,6,7,8', [1, 2, [3, 4], 5, [[[6], 7], 8]])
        assertArrayToPrimitive(
            String, '[object Object],[object Object]', [{}, {}])
        assertArrayToPrimitive(
            String,
            '0,1,,true,false,hello', [0, 1, None, True, False, 'hello'])

        assertArrayToPrimitive(Number, 0, [])
        assertArrayToPrimitive(Number, 0, [0])
        assertArrayToPrimitive(Number, 1, [1])
        assertArrayToPrimitive(Number, 1, ['1'])
        assertArrayToPrimitive(Number, 'NaN', [1, 2])
        assertArrayToPrimitive(Number, 1, [[[1]]])

        assertArrayToPrimitive(Number, 'NaN', [True])
        assertArrayToPrimitive(Number, 'NaN', [False])
        assertArrayToPrimitive(Number, 2748, ['  0002748 '])
        assertArrayToPrimitive(Number, 2748, ['  0xabc  '])
        assertArrayToPrimitive(Number, 'NaN', ['  00xabc  '])

    def test_to_primitive_object(self):
        # TODO validate that all the folded_type returned is expected
        self.assertEqual('[object Object]', to_primitive(
            FoldedFragment({}, Object), String).value)
        self.assertEqual('NaN', to_primitive(
            FoldedFragment({}, Object), Number).value)

    def test_to_primitive_other(self):
        # TODO validate that all the folded_type returned is expected
        fragments = [
            FoldedFragment(0, Number),
            FoldedFragment('hello', String),
            FoldedFragment(True, Boolean),
            FoldedFragment(None, Null),
        ]
        for fragment in fragments:
            self.assertIs(fragment, to_primitive(fragment, String))
        for fragment in fragments:
            self.assertIs(fragment, to_primitive(fragment, Number))

    def test_to_boolean(self):
        self.assertTrue(to_boolean(FoldedFragment([], Array)))
        self.assertTrue(to_boolean(FoldedFragment({}, Object)))
        self.assertFalse(to_boolean(FoldedFragment(None, Null)))
        self.assertTrue(to_boolean(FoldedFragment(True, Boolean)))
        self.assertFalse(to_boolean(FoldedFragment(False, Boolean)))
        self.assertTrue(to_boolean(FoldedFragment(1, Number)))
        self.assertFalse(to_boolean(FoldedFragment(0, Number)))
        self.assertFalse(to_boolean(FoldedFragment('NaN', Number)))
        self.assertTrue(to_boolean(FoldedFragment('hello', String)))
        self.assertFalse(to_boolean(FoldedFragment('', String)))

    def test_to_number(self):
        self.assertEqual(0, to_number(FoldedFragment([], Array)))
        self.assertEqual(1, to_number(FoldedFragment([[['1']]], Array)))
        self.assertEqual(1, to_number(FoldedFragment(True, Boolean)))
        self.assertEqual(0, to_number(FoldedFragment(False, Boolean)))
        value = 5343
        self.assertIs(value, to_number(FoldedFragment(value, Number)))
        self.assertEqual(0, to_number(FoldedFragment(None, Null)))
        self.assertEqual(1234, to_number(FoldedFragment('1234', Array)))
        self.assertEqual('NaN', to_number(FoldedFragment({}, Object)))

        # for completeness, no idea how might other asttypes slip through
        self.assertEqual('NaN', to_number(FoldedFragment([], Block)))

    def test_to_string(self):
        self.assertEqual('', to_string(FoldedFragment([], Array)))
        self.assertEqual('true', to_string(FoldedFragment(True, Boolean)))
        self.assertEqual('false', to_string(FoldedFragment(False, Boolean)))
        self.assertEqual('null', to_string(FoldedFragment(None, Null)))
        self.assertEqual(
            '12345.67', to_string(FoldedFragment(12345.67, Number)))
        value = 'hello world'
        self.assertIs(value, to_string(FoldedFragment(value, String)))
        self.assertEqual(
            '[object Object]', to_string(FoldedFragment({}, Object)))

        # for completeness, there could be definitions where unsupported
        # asttypes can slip through, just ensure they output an empty
        # string if the produced value is not a string.
        self.assertEqual('', to_string(FoldedFragment([], Block)))
        # for string values, enclose them as a format token.
        self.assertEqual(
            '{value}', to_string(FoldedFragment('value', Identifier)))

    def test_to_int32(self):
        self.assertEqual(0, to_int32(FoldedFragment([], Array)))
        self.assertEqual(1, to_int32(FoldedFragment([[['1']]], Array)))
        self.assertEqual(1, to_int32(FoldedFragment(True, Boolean)))
        self.assertEqual(0, to_int32(FoldedFragment(False, Boolean)))

        self.assertEqual(54321, to_int32(FoldedFragment(54321, Number)))

        self.assertEqual(0, to_int32(FoldedFragment(None, Null)))
        self.assertEqual(1234, to_int32(FoldedFragment('1234', Array)))
        self.assertEqual(0, to_int32(FoldedFragment({}, Object)))

        maxint32 = 2147483647
        overint32 = 2147483648
        self.assertEqual(
            maxint32, to_int32(FoldedFragment(maxint32, Number)))
        self.assertEqual(
            - overint32, to_int32(FoldedFragment(overint32, Number)))

        # for completeness, no idea how might other asttypes slip through
        self.assertEqual(0, to_int32(FoldedFragment([], Block)))


class ExtractorUnparserErrorTestCase(unittest.TestCase):

    def test_bad_boolean(self):
        unparser = Unparser()
        ast = parse('thing = false;')
        # mangle the type such that the lookup fails
        ast.children()[0].expr.right.value = 'none'
        with self.assertRaises(ValueError) as e:
            list(unparser(ast))
        self.assertIn(
            "'none' is not a JavaScript boolean value",
            e.exception.args[0],
        )

    def assert_definitions_fault(
            self, errorcls, definitions, src, msg, result):
        unparser = Unparser(definitions=definitions)
        ast = parse(src)
        with self.assertRaises(errorcls) as e:
            dict(unparser(ast))
        self.assertIn(msg, str(e.exception))

        err = setup_logger(self, extractor_logger)
        unparser = Unparser(definitions=definitions, dispatcher_cls=Dispatcher)
        ast = parse(src)
        self.assertEqual(result, dict(unparser(ast)))
        self.assertIn(msg, err.getvalue())

    def test_definitions_fault_handling(self):
        class BadAttr(Attr):
            def __call__(self, walk, dispatcher, node):
                # rather than going through dispatcher.walk, yield this
                # unwrapped type (i.e. not via walk or dispatcher.token
                yield self._getattr(dispatcher, node)

        mismatched = {}
        mismatched.update(definitions)
        mismatched['Assign'] = (Attr('left'), BadAttr('op'), Attr('right'),)

        self.assert_definitions_fault(
            TypeError, mismatched,
            'a = 1;{}',
            "'=' is not an instance of ExtractedFragment",
            {
                Identifier: ['a'],
                # Assign: ['='],
                Number: [1],
                # sentinel node to ensure no other premature termination
                Block: [{}],
            },
        )

    def test_definitions_groupasunary_errors(self):
        # for the case where certain types have not been properly
        # reduced to a supported grouping
        faulty = {}
        faulty.update(definitions)
        faulty['Array'] = (GroupAsUnaryExprPlus(),)
        faulty['UnaryExpr'] = (GroupAsUnaryExpr(),)

        self.assert_definitions_fault(
            TypeError, faulty,
            "a = [1, 2, 3]",
            "Ruletype token 'GroupAsUnaryExprPlus' expects a 'UnaryExpr', "
            "got 'Array'",
            {'a': ''},
        )
        self.assert_definitions_fault(
            NotImplementedError, faulty,
            "a = +1",
            "",
            {'a': ''},
        )

    def test_definitions_groupasbin_errors(self):
        # for the case where certain types have not been properly
        # reduced to a supported grouping
        faulty = {}
        faulty.update(definitions)
        faulty['Array'] = (GroupAsBinOpPlus(),)

        self.assert_definitions_fault(
            TypeError, faulty,
            "a = [1, 2, 3]",
            "Ruletype token 'GroupAsBinOpPlus' expects a 'BinOp', got 'Array'",
            {'a': ''},
        )

        faulty['BinOp'] = (GroupAsBinOp(),)
        self.assert_definitions_fault(
            NotImplementedError, faulty,
            "a = 1 + 1; b = 'x' + 'x'",
            "",
            {'a': '', 'b': 'NaN'},
        )

        faulty['BinOp'] = (GroupAsBinOpBitwise(),)
        self.assert_definitions_fault(
            NotImplementedError, faulty,
            "a = 1 | 1; b = 'x' | 'x'",
            "",
            {'a': '', 'b': ''},
        )

    def test_definitions_groupasbin_incompat(self):
        # for the case where certain types have not been properly
        # reduced to a supported grouping
        faulty = {}
        faulty.update(definitions)
        faulty['Array'] = (JoinAttr('items'),)
        faulty['BinOp'] = (GroupAsBinOpPlus(),)

        self.assert_definitions_fault(
            ValueError, faulty,
            "a = '' + [1, 2, 3]",
            "Ruletype token 'GroupAsBinOpPlus' unable to process output "
            "produced by the definition used on <Array @1:10 ...>, as it "
            "yielded more than one fragment (first two fragments are "
            "ExtractedFragment(value=1, node=<Number @1:11 value='1'>, "
            "folded_type=<class 'calmjs.parse.asttypes.Number'>) and "
            "ExtractedFragment(value=2, node=<Number @1:14 value='2'>, "
            "folded_type=<class 'calmjs.parse.asttypes.Number'>))",
            {'a': ''},
        )


class ExtractorUnparserTestCase(unittest.TestCase):

    def test_empty_program(self):
        unparser = Unparser()
        ast = parse('')
        self.assertEqual(dict(unparser(ast)), {})

    def test_empty_statements(self):
        unparser = Unparser()
        ast = parse(";;;")
        self.assertEqual(dict(unparser(ast)), {})

    def test_ignoreed_statements(self):
        unparser = Unparser()
        ast = parse("""
        ;
        debugger;
        continue;
        break;
        """)
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
        var r = s = /abc/;
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'a': 'hello',
            'b': 'hello',
            'c': 'hello',
            'd': 'hello',
            'x': 42,
            'y': 42,
            'z': 42,
            'r': '/abc/',
            's': '/abc/',
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
            d: /a/,
            e: /a/i,
        }
        ''')
        self.assertEqual(dict(unparser(ast)), {
            'obj_a': {'a': 1, 'b': 2, 'c': [1, 2], 'd': '/a/', 'e': '/a/i'}
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

    def test_bracket_accessor_on_string(self):
        unparser = Unparser()
        ast = parse('''
        value = 'hello'[1];
        ''')
        # bracket accessor won't try to resolve the value
        self.assertEqual(dict(unparser(ast)), {
            'value': 'hello[1]',
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
        b = !'hello' + ' ' + 'world';
        """)
        self.assertEqual(dict(unparser(ast)), {
            'a': "'hello' + ' ' + 'world'",
            'b': "!'hello' + ' ' + 'world'",
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
                ['i < j && j < 15', 'i', '++j', {Block: [{'x': 'i * j'}]}],
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
          continue;
        }

        while (true) {
          x = 2;
          y = 4;
          continue foo;
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

    def test_while_assign(self):
        unparser = Unparser()
        ast = parse("""
        while (x = x + 1) {
          y = 2;
          break;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            While: [
                [[('x', 'x + 1')], {Block: [{
                    'y': 2,
                }]}],
            ],
        })

    def test_with_statement(self):
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

    def test_with_statement_with_assign(self):
        unparser = Unparser()
        ast = parse("""
        with (x = 3) {
          x = x * 2;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            With: [
                [[('x', 3)], {Block: [{
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

    def test_try_catch_finally_statement(self):
        unparser = Unparser()
        ast = parse("""
        try {
            var x = 100;
            y = 111;
        }
        catch (e) {
            var x = 200;
            y = 222;
        }
        finally {
            z = 1;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            Try: [[{
                'x': 100,
                'y': 111,
            }, {
                Catch: [['e', {
                    'x': 200,
                    'y': 222,
                }]],
            }, {
                Finally: [[{
                    'z': 1,
                }]],
            }]],
        })

    def test_try_catch_try_finally_statement(self):
        unparser = Unparser()
        ast = parse("""
        try {
            var x = 100;
            y = 111;
        }
        catch (e) {
            var x = 200;
            y = 222;
        }

        try {
            var x = 10;
            y = 11;
        }
        finally {
            z = 3;
        }
        """)
        self.assertEqual(dict(unparser(ast)), {
            Try: [[{
                'x': 100,
                'y': 111,
            }, {
                Catch: [['e', {
                    'x': 200,
                    'y': 222,
                }]],
            }], [{
                'x': 10,
                'y': 11,
            }, {
                Finally: [[{
                    'z': 3,
                }]],
            }]],
        })

    def test_unary_expr(self):
        unparser = Unparser()
        ast = parse("""
        ++obj;
        delete obj;
        +42;
        -42;  // no negative numbers in ast; unary `-` negates positives
        !"foo";
        """)
        self.assertEqual(dict(unparser(ast)), {
            # UnaryExpr instead of Number, because that's the most outer
            # node captured; a "neat" demonstration of a slippage in the
            # ECMAScript syntax and semantics in its specifications.
            UnaryExpr: ['++obj', 'delete obj', 42, -42, '!"foo"'],
        })

    def test_postfix_op(self):
        unparser = Unparser()
        ast = parse("""
        i++;
        j--;
        """)
        self.assertEqual(dict(unparser(ast)), {
            Identifier: ['i', 'j'],
        })

    def test_elision(self):
        unparser = Unparser()
        ast = parse("""
        i = [,,,]
        """)
        self.assertEqual(dict(unparser(ast)), {'i': []})


class ExtractorTestCase(unittest.TestCase):
    """
    Simply test via the simplified constructor
    """

    def test_extractor_empty(self):
        ast = parse('')
        self.assertEqual({}, dict(extractor()(ast)))

    def test_bad_boolean_skipped(self):
        err = setup_logger(self, extractor_logger)
        ast = parse('thing = false;')
        # mangle the type such that the lookup fails
        ast.children()[0].expr.right.value = 'none'
        # use the ast_to_dict function
        result = ast_to_dict(ast, ignore_errors=True)
        self.assertIn(
            "failed to process node <Boolean @1:9 value='none'> with rule "
            "'RawBoolean' to an extracted value; cause: ValueError: ",
            err.getvalue(),
        )
        self.assertIn(
            "'none' is not a JavaScript boolean value",
            err.getvalue(),
        )
        # default value current an empty string.
        self.assertEqual(result, {'thing': ''})

    def test_binop_plus(self):
        ast = parse("""
        greetings = 'Hello, ' + 'World!';
        three = 1 + 2;
        _x1 = 'x' + 1;
        _1x = 1 + 'x';
        six = 1 + 2 + 3;
        objobj = {} + {};
        arrarr = [] + [];
        str12 = [1] + [2];
        strarr = [1, 2, 3] + [4, 5, 6];
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['greetings'], 'Hello, World!')
        self.assertEqual(result['three'], 3)
        self.assertEqual(result['_x1'], 'x1')
        self.assertEqual(result['_1x'], '1x')
        self.assertEqual(result['six'], 6)
        self.assertEqual(result['objobj'], '[object Object][object Object]')
        self.assertEqual(result['arrarr'], '')
        self.assertEqual(result['str12'], '12')
        self.assertEqual(result['strarr'], '1,2,34,5,6')

    def test_binop_plus_format(self):
        ast = parse("""
        name = "John";
        greetings = 'Hello, ' + name + '!';
        accessors = 'Poking at obj ' + a.b.c + ':' + thing[1]['abc'].x + '.';
        f_call = 'Function call: ' + f(a, b, c);
        namename = name + name;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['name'], 'John')
        self.assertEqual(result['greetings'], 'Hello, {name}!')
        self.assertEqual(
            result['accessors'], 'Poking at obj {a.b.c}:{thing[1][abc].x}.')
        self.assertEqual(
            result['f_call'], 'Function call: {}')
        self.assertEqual(result['namename'], '{name}{name}')

    def test_binop_minus(self):
        ast = parse("""
        greetings = 'Hello, ' - 'World!';
        neg1 = 1 - 2;
        _x1 = 'x' - 1;
        _1x = 1 - 'x';
        neg4 = 1 - 2 - 3;
        wat = 'x' - 'x';
        objobj = {} - {};
        arrarr = [] - [];
        arrneg1 = [1] - [2];
        id = id1 - id2;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['greetings'], 'NaN')
        self.assertEqual(result['neg1'], -1)
        self.assertEqual(result['_x1'], 'NaN')
        self.assertEqual(result['_1x'], 'NaN')
        self.assertEqual(result['neg4'], -4)
        self.assertEqual(result['wat'], 'NaN')
        self.assertEqual(result['objobj'], 'NaN')
        self.assertEqual(result['arrarr'], 0)
        self.assertEqual(result['arrneg1'], -1)
        self.assertEqual(result['id'], 'NaN')

    def test_binop_mult(self):
        ast = parse("""
        twelve = 3 * 4;
        sixty = 3 * 4 * 5;
        wot = 'x' * 'x';
        wut = 'x' * 'x' * 'x';
        // currently not working because NaN is treated as an identifier
        // check = NaN * NaN
        // currently done via grouping test
        objobj = {} * {};
        arrarr = [] * [];
        arrmult = [1] * [2];
        id = id1 * id2;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['twelve'], 12)
        self.assertEqual(result['sixty'], 60)
        self.assertEqual(result['wot'], 'NaN')
        self.assertEqual(result['wut'], 'NaN')
        self.assertEqual(result['objobj'], 'NaN')
        self.assertEqual(result['arrarr'], 0)
        self.assertEqual(result['arrmult'], 2)
        self.assertEqual(result['id'], 'NaN')

    def test_binop_div(self):
        ast = parse("""
        threequarters = 3 / 4;
        ten = 1000 / 10 / 10;
        wot = 'x' / 'x';
        wut = 'x' / 'x' / 'x';
        objobj = {} / {};
        arrarr = [] / [];
        half = [1] / [2];
        id = id1 / id2;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['threequarters'], 0.75)
        self.assertEqual(result['ten'], 10)
        self.assertEqual(result['wot'], 'NaN')
        self.assertEqual(result['wut'], 'NaN')
        self.assertEqual(result['objobj'], 'NaN')
        self.assertEqual(result['arrarr'], 'NaN')
        self.assertEqual(result['half'], 0.5)
        self.assertEqual(result['id'], 'NaN')

    def test_binop_mod(self):
        ast = parse("""
        zero = 2 % 2;
        one = 4 % 3;
        two = 13 % 11 % 3
        wot = 'x' % 'x';
        wut = 'x' % 'x' % 'x';
        objobj = {} % {};
        arrarr = [] % [];
        three = [3] % [4];
        id = id1 % id2;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['zero'], 0)
        self.assertEqual(result['one'], 1)
        self.assertEqual(result['two'], 2)
        self.assertEqual(result['wot'], 'NaN')
        self.assertEqual(result['wut'], 'NaN')
        self.assertEqual(result['objobj'], 'NaN')
        self.assertEqual(result['arrarr'], 'NaN')
        self.assertEqual(result['three'], 3)
        self.assertEqual(result['id'], 'NaN')

    def test_binop_leftshift(self):
        ast = parse("""
        eight = 2 << 2;
        eightyeight = 11 << 3;
        wot = 'x' << 'x';
        objobj = {} << {};
        arrarr = [] << [];
        six = [3] << [1];
        sixteen = '4' << '2';
        id = id1 << id2;
        neg2 = 2147483647 << 1;
        negmax = 1 << 31;
        negmax2 = 2147483647 << 31;
        negspot = -2147483649 << 111;
        negtwo = -1 << -31;
        negone = -1 << -32;
        negmax3 = -1 << -33;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['eight'], 8)
        self.assertEqual(result['eightyeight'], 88)
        self.assertEqual(result['wot'], 0)
        self.assertEqual(result['objobj'], 0)
        self.assertEqual(result['arrarr'], 0)
        self.assertEqual(result['six'], 6)
        self.assertEqual(result['sixteen'], 16)
        self.assertEqual(result['id'], 0)
        self.assertEqual(result['neg2'], -2)
        self.assertEqual(result['negmax'], -2147483648)
        self.assertEqual(result['negmax2'], -2147483648)
        self.assertEqual(result['negspot'], -32768)
        self.assertEqual(result['negtwo'], -2)
        self.assertEqual(result['negone'], -1)
        self.assertEqual(result['negmax3'], -2147483648)

    def test_binop_rightshift(self):
        ast = parse("""
        eight = 32 >> 2;
        eightyeight = 704 >> 3;
        wot = 'x' >> 'x';
        objobj = {} >> {};
        arrarr = [] >> [];
        six = [12] >> [1];
        sixteen = '259' >> '4';
        id = id1 >> id2;
        neg2 = -4 >> 1;
        negmax = 2147483648 >> [];
        max = 2147483647 >> 32;
        zero = 32767 >> 18;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['eight'], 8)
        self.assertEqual(result['eightyeight'], 88)
        self.assertEqual(result['wot'], 0)
        self.assertEqual(result['objobj'], 0)
        self.assertEqual(result['arrarr'], 0)
        self.assertEqual(result['six'], 6)
        self.assertEqual(result['sixteen'], 16)
        self.assertEqual(result['id'], 0)
        self.assertEqual(result['neg2'], -2)
        self.assertEqual(result['negmax'], -2147483648)
        self.assertEqual(result['max'], 2147483647)
        self.assertEqual(result['zero'], 0)

    def test_binop_signedrightshift(self):
        ast = parse("""
        eight = 32 >>> 2;
        eightyeight = 704 >>> 3;
        wot = 'x' >>> 'x';
        objobj = {} >>> {};
        arrarr = [] >>> [];
        six = [12] >>> [1];
        sixteen = '259' >>> '4';
        id = id1 >>> id2;
        neg2 = -4 >>> 1;
        negmax = 2147483648 >>> [];
        max = -1 >>> 0;
        zero = 4294967296 >>> 0;
        overflow = 32767 >>> 18;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['eight'], 8)
        self.assertEqual(result['eightyeight'], 88)
        self.assertEqual(result['wot'], 0)
        self.assertEqual(result['objobj'], 0)
        self.assertEqual(result['arrarr'], 0)
        self.assertEqual(result['six'], 6)
        self.assertEqual(result['sixteen'], 16)
        self.assertEqual(result['id'], 0)
        self.assertEqual(result['neg2'], 2147483646)
        self.assertEqual(result['negmax'], 2147483648)
        self.assertEqual(result['max'], 4294967295)
        self.assertEqual(result['zero'], 0)
        self.assertEqual(result['overflow'], 0)

    def test_binop_bitwise(self):
        ast = parse("""
        and_ = 12 & 10;
        xor_ = 12 ^ 10;
        or_ = 12 | 10;
        zero = 4294967296 & 4294967296;
        minus1 = 4294967295 & 4294967295;
        oneoneone = [111] & '111';
        nothing = {} ^ [];
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['and_'], 8)
        self.assertEqual(result['xor_'], 6)
        self.assertEqual(result['or_'], 14)
        self.assertEqual(result['zero'], 0)
        self.assertEqual(result['minus1'], -1)
        self.assertEqual(result['oneoneone'], 111)
        self.assertEqual(result['nothing'], 0)

    def test_binop_logical(self):
        ast = parse("""
        zero = ['asdf'] && 0 && 1;
        one = '1' && true && 1;
        two = '2' || 0 && 1;
        three = '33' && 0 || [3];
        wut = unknown && 1;
        none = unknown || null;
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['zero'], 0)
        self.assertEqual(result['one'], 1)
        self.assertEqual(result['two'], '2')
        self.assertEqual(result['three'], [3])
        # as the value bound to any identifier is assumed to be null,
        # the "variable" is returned as-is.
        self.assertEqual(result['wut'], 'unknown')
        self.assertEqual(result['none'], None)

    def test_binop_folding_various(self):
        ast = parse("""
        ten = 1 + 2 + 3 + 4;
        eleven = 1 + 2 * 3 + 4;
        lel = 'x' * 'x' + 'x'
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['ten'], 10)
        self.assertEqual(result['eleven'], 11)
        self.assertEqual(result['lel'], 'NaNx')

    def test_binop_folding_with_grouping(self):
        ast = parse("""
        twentysix = (1 + 2) * (3 + 4) + 5;
        check = ('x' * 'x') * ('x' * 'x');
        """)
        result = ast_to_dict(ast, fold_ops=True)
        self.assertEqual(result['twentysix'], 26)
        self.assertEqual(result['check'], 'NaN')

    def test_unary_expr_plusminus_folding(self):
        unparser = Unparser()
        ast = parse("""
        plus = +'42';
        neg = -'42';
        plusobj = +{};
        negobj = -{};
        """)
        self.assertEqual(dict(unparser(ast)), {
            'plus': 42,
            'neg': -42,
            'plusobj': 'NaN',
            'negobj': 'NaN',
        })

    def test_unary_expr_bitwise_not_folding(self):
        ast = parse("""
        nu = ~null;
        nn = ~NaN;
        neg1 = ~0;
        zero = ~'-1';
        negthreethree = ~[32];
        negtwofivesix = ~'0xff';
        bigzero = ~4294967295;
        smallneg1 = ~{};
        max31 = ~2147483648;
        min31 = ~2147483647;
        """)
        self.assertEqual(ast_to_dict(ast, fold_ops=True), {
            'nn': -1,
            'nu': -1,
            'neg1': -1,
            'zero': 0,
            'negthreethree': -33,
            'negtwofivesix': -256,
            'bigzero': 0,
            'smallneg1': -1,
            'max31': 2147483647,
            'min31': -2147483648,
        })

    def test_unary_expr_logical_not_folding(self):
        ast = parse("""
        nu = !null;
        nn = !NaN;
        t = !0;
        f = !1;
        tt = !false;
        ff = ![0];
        ttt = !'';
        fff = !{};
        """)
        self.assertEqual(ast_to_dict(ast, fold_ops=True), {
            'nn': True,
            'nu': True,
            't': True,
            'f': False,
            'tt': True,
            'ff': False,
            'ttt': True,
            'fff': False,
        })

    def test_unary_expr_various_folding(self):
        ast = parse("""
        de = delete obj;
        i = +1;
        j = -1;
        """)
        self.assertEqual(ast_to_dict(ast, fold_ops=True), {
            'de': 'delete obj',
            'i': 1,
            'j': -1,
        })
