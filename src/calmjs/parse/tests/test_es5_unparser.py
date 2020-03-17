# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import textwrap
from functools import partial

from calmjs.parse import asttypes
from calmjs.parse import es5
from calmjs.parse.ruletypes import Declare
from calmjs.parse.ruletypes import Space
from calmjs.parse.ruletypes import RequiredSpace
from calmjs.parse.ruletypes import Text
from calmjs.parse.parsers.es5 import parse
from calmjs.parse.walkers import Walker

from calmjs.parse.handlers.core import layout_handler_space_drop
from calmjs.parse.handlers.core import default_rules
from calmjs.parse.handlers.core import minimum_rules
from calmjs.parse.handlers.indentation import indent

from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.unparsers.es5 import definitions
from calmjs.parse.unparsers.es5 import pretty_print
from calmjs.parse.unparsers.es5 import minify_printer
from calmjs.parse.unparsers.es5 import minify_print

from calmjs.parse.testing.util import build_equality_testcase


def quad(items):
    return [i[:4] for i in items]


class BaseVisitorTestCase(unittest.TestCase):
    # Many of these tests are here are for showing individual fixes that
    # were done to other classes in order to properly support the source
    # map feature.

    def test_empty_program(self):
        unparser = Unparser()
        ast = parse('')
        self.assertEqual(quad(unparser(ast)), [
        ])

    def test_basic_integer(self):
        unparser = Unparser()
        ast = parse('0;')
        self.assertEqual(quad(unparser(ast)), [
            ('0', 1, 1, None),
            (';', 1, 2, None),
            ('\n', 0, 0, None),
        ])

    def test_basic_var_space_standard(self):
        unparser = Unparser()
        ast = parse('var x = 0;')
        self.assertEqual(quad(unparser(ast)), [
            ('var', 1, 1, None), (' ', 0, 0, None), ('x', 1, 5, None),
            (' ', 0, 0, None), ('=', 1, 7, None), (' ', 0, 0, None),
            ('0', 1, 9, None), (';', 1, 10, None),
            ('\n', 0, 0, None),
        ])

    def test_basic_var_decl(self):
        declared_vars = []

        def declare(dispatcher, node):
            declared_vars.append(node.value)

        unparser = Unparser(deferrable_handlers={
            Declare: declare,
        })
        ast = parse('var x = 0;')
        # just run through the ast
        quad(unparser(ast))
        self.assertEqual(['x'], declared_vars)

    def test_basic_var_space_drop(self):
        unparser = Unparser(layout_handlers={
            Space: layout_handler_space_drop,
            RequiredSpace: layout_handler_space_drop,
        })
        ast = parse('var x = 0;\nvar y = 0;')
        self.assertEqual(quad(unparser(ast)), [
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
        # if there are no rules provided, there will also be no layout
        # handlers - not very useful as note that there is now no
        # separation between `var` and `x`.
        unparser = Unparser(rules=())
        ast = parse('var x = 0;')
        self.assertEqual(quad(unparser(ast)), [
            ('var', 1, 1, None), ('x', 1, 5, None), ('=', 1, 7, None),
            ('0', 1, 9, None),
        ])

    def test_simple_identifier(self):
        unparser = Unparser()
        ast = parse('this;')
        self.assertEqual(quad(unparser(ast)), [
            ('this', 1, 1, None), (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_simple_identifier_unmapped(self):
        # if the definition contains unmapped entries
        new_definitions = {}
        new_definitions.update(definitions)
        new_definitions['This'] = (Text(value='this', pos=None),)
        unparser = Unparser(definitions=new_definitions)
        ast = parse('this;')
        self.assertEqual(quad(unparser(ast)), [
            ('this', None, None, None), (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_empty_object(self):
        unparser = Unparser()
        ast = parse('thing = {};')
        self.assertEqual(quad(unparser(ast)), [
            ('thing', 1, 1, None), (' ', 0, 0, None), ('=', 1, 7, None),
            (' ', 0, 0, None), ('{', 1, 9, None), ('}', 1, 10, None),
            (';', 1, 11, None), ('\n', 0, 0, None),
        ])

    def test_simple_function_declare(self):
        unparser = Unparser()
        ast = parse('function foo(){}')
        self.assertEqual(quad(unparser(ast)), [
            ('function', 1, 1, None), (' ', 0, 0, None), ('foo', 1, 10, None),
            ('(', 1, 13, None), (')', 1, 14, None), (' ', 0, 0, None),
            ('{', 1, 15, None), ('\n', 0, 0, None), ('}', 1, 16, None),
            ('\n', 0, 0, None),
        ])

    def test_simple_function_invoke(self):
        unparser = Unparser()
        ast = parse('foo();')
        self.assertEqual(quad(unparser(ast)), [
            ('foo', 1, 1, None), ('(', 1, 4, None), (')', 1, 5, None),
            (';', 1, 6, None), ('\n', 0, 0, None),
        ])

    def test_new_new(self):
        unparser = Unparser()
        ast = parse('new new T();')
        self.assertEqual(quad(unparser(ast)), [
            ('new', 1, 1, None), (' ', 0, 0, None),
            ('new', 1, 5, None), (' ', 0, 0, None),
            ('T', 1, 9, None), ('(', 1, 10, None), (')', 1, 11, None),
            (';', 1, 12, None), ('\n', 0, 0, None),
        ])

    def test_getter(self):
        unparser = Unparser()
        ast = parse('x = {get p() {}};')
        self.assertEqual(quad(unparser(ast)), [
            ('x', 1, 1, None), (' ', 0, 0, None), ('=', 1, 3, None),
            (' ', 0, 0, None), ('{', 1, 5, None), ('\n', 0, 0, None),
            ('get', 1, 6, None), (' ', 0, 0, None), ('p', 1, 10, None),
            ('(', 1, 11, None), (')', 1, 12, None),
            (' ', 0, 0, None), ('{', 1, 14, None), ('\n', 0, 0, None),
            ('}', 1, 15, None), ('\n', 0, 0, None),
            ('}', 1, 16, None), (';', 1, 17, None), ('\n', 0, 0, None),
        ])

    def test_setter(self):
        unparser = Unparser()
        ast = parse('x = {set p(a) {}};')
        self.assertEqual(quad(unparser(ast)), [
            ('x', 1, 1, None), (' ', 0, 0, None), ('=', 1, 3, None),
            (' ', 0, 0, None), ('{', 1, 5, None), ('\n', 0, 0, None),
            ('set', 1, 6, None), (' ', 0, 0, None), ('p', 1, 10, None),
            ('(', 1, 11, None), ('a', 1, 12, None), (')', 1, 13, None),
            (' ', 0, 0, None), ('{', 1, 15, None), ('\n', 0, 0, None),
            ('}', 1, 16, None), ('\n', 0, 0, None),
            ('}', 1, 17, None), (';', 1, 18, None), ('\n', 0, 0, None),
        ])

    def test_switch_case_default_case(self):
        unparser = Unparser()
        ast = parse('switch (v) { case true: break; default: case false: }')
        self.assertEqual(quad(unparser(ast)), [
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
        unparser = Unparser()
        ast = parse('[];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None), (']', 1, 2, None),
            (';', 1, 3, None), ('\n', 0, 0, None),
        ])

    def test_elision_1(self):
        unparser = Unparser()
        ast = parse('[,];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None), (',', 1, 2, None), (']', 1, 3, None),
            (';', 1, 4, None), ('\n', 0, 0, None),
        ])

    def test_elision_2(self):
        unparser = Unparser()
        ast = parse('[,,];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None), (',,', 1, 2, None), (']', 1, 4, None),
            (';', 1, 5, None), ('\n', 0, 0, None),
        ])

    def test_elision_4(self):
        unparser = Unparser()
        ast = parse('[,,,,];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None), (',,,,', 1, 2, None), (']', 1, 6, None),
            (';', 1, 7, None), ('\n', 0, 0, None),
        ])

    def test_elision_v3(self):
        unparser = Unparser()
        ast = parse('[1,,,,];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None), ('1', 1, 2, None), (',', 0, 0, None),
            (',,,', 1, 4, None), (']', 1, 7, None),
            (';', 1, 8, None), ('\n', 0, 0, None),
        ])

    def test_elision_vv3(self):
        unparser = Unparser()
        ast = parse('[1, 2,,,,];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None),
            ('1', 1, 2, None), (',', 0, 0, None), (' ', 0, 0, None),
            ('2', 1, 5, None), (',', 0, 0, None),  # ditto for this
            (',,,', 1, 7, None), (']', 1, 10, None),
            (';', 1, 11, None), ('\n', 0, 0, None),
        ])

    def test_elision_v3v(self):
        unparser = Unparser()
        ast = parse('[1,,,, 1];')
        self.assertEqual(quad(unparser(ast)), [
            ('[', 1, 1, None), ('1', 1, 2, None), (',', 0, 0, None),
            (',,,', 1, 4, None),
            (' ', 0, 0, None),
            ('1', 1, 8, None), (']', 1, 9, None),
            (';', 1, 10, None), ('\n', 0, 0, None),
        ])

    def test_elision_1v1(self):
        unparser = Unparser()
        ast = parse('[, 1,,];')
        self.assertEqual(list(i[:4] for i in unparser(ast)), [
            ('[', 1, 1, None),
            (',', 1, 2, None), (' ', 0, 0, None),
            ('1', 1, 4, None), (',', 0, 0, None),
            (',', 1, 6, None), (']', 1, 7, None),
            (';', 1, 8, None), ('\n', 0, 0, None),
        ])

    def test_elision_splits_spaces(self):
        unparser = Unparser()
        # note the spaces and how they are ignored
        ast = parse('[, 1, , 2 , ,,,,, 3,, ,,,, ,,,4,];')
        self.assertEqual(list(i[:4] for i in unparser(ast)), [
            ('[', 1, 1, None), (',', 1, 2, None), (' ', 0, 0, None),
            ('1', 1, 4, None), (',', 0, 0, None),
            (',', 1, 7, None), (' ', 0, 0, None),
            ('2', 1, 9, None), (',', 0, 0, None),
            (',,,,,', 1, 13, None), (' ', 0, 0, None),
            ('3', 1, 19, None), (',', 0, 0, None),
            # though rowcols of the starting comma are maintained.
            (',,,,,,,,', 1, 21, None), (' ', 0, 0, None),
            ('4', 1, 31, None),
            (']', 1, 33, None),
            (';', 1, 34, None),
            ('\n', 0, 0, None),
        ])

    def test_elision_splits_newlines(self):
        # the newlines in this case will be completely dropped, but
        # again as long as the first comma is not shifted, it will be
        # a syntactically accurate reconstruction, while the sourcemap
        # that is generated isn't completely reflective of what the
        # original is.
        unparser = Unparser()
        ast = parse(textwrap.dedent('''
        [, 1,
        , 2 , ,,
        ,,, 3,,
        ,,,,
        ,,,4,];
        ''').strip())
        self.assertEqual(list(i[:4] for i in unparser(ast)), [
            ('[', 1, 1, None), (',', 1, 2, None), (' ', 0, 0, None),
            ('1', 1, 4, None), (',', 0, 0, None),
            (',', 2, 1, None), (' ', 0, 0, None),
            ('2', 2, 3, None), (',', 0, 0, None), (',,,,,', 2, 7, None),
            (' ', 0, 0, None),
            ('3', 3, 5, None),
            (',', 0, 0, None),
            (',,,,,,,,', 3, 7, None),
            (' ', 0, 0, None),
            ('4', 5, 4, None),
            (']', 5, 6, None),
            (';', 5, 7, None),
            ('\n', 0, 0, None),
        ])

    def test_if_else_block(self):
        unparser = Unparser()
        ast = parse('if (true) {} else {}')
        self.assertEqual([tuple(t[:4]) for t in (unparser(ast))], [
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
        unparser = Unparser()
        self.assertEqual([tuple(t) for t in (unparser(ast))], [
            ('foo', None, None, None, NotImplemented),
            ('(', None, None, None, NotImplemented),
            ('x', None, None, None, NotImplemented),
            (')', None, None, None, NotImplemented),
            (';', None, None, None, None),
            ('\n', 0, 0, None, None),
        ])

    def test_remap_function_call(self):
        # a form of possible manual replacement call.
        walker = Walker()
        src = textwrap.dedent("""
        (function(foo, bar, arg1, arg2) {
            foo(arg1);
            bar(arg2);
        })(foo, bar, arg1, arg2);
        """).strip()
        ast = parse(src)
        block = walker.extract(ast, lambda n: isinstance(n, asttypes.FuncExpr))

        for stmt in block.elements:
            fc = stmt.expr
            stmt.expr = asttypes.FunctionCall(
                args=fc.args, identifier=asttypes.DotAccessor(
                    node=asttypes.Identifier(value='window'),
                    identifier=fc.identifier))

        # Now try to render.
        unparser = Unparser()
        self.assertEqual([tuple(t[:4]) for t in (unparser(ast))], [
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

    def test_minify_print_obfuscate_skip_keywords(self):
        # test that the obfuscated minifier for es5 will skip the first
        # reserved keyword symbol found, i.e. 'do'
        # Note that while these identifiers can be easily generated by
        # a simple for loop, it can also be done by iterating through
        # an enumerated instance of the obfuscation.NameGenerator class
        # and stop at the index where the target token (in this case
        # 'do') is.
        tree = parse(textwrap.dedent("""
        (function() {
          var i_0, i_1, i_2, i_3, i_4, i_5, i_6, i_7, i_8, i_9, i_10, i_11,
            i_12, i_13, i_14, i_15, i_16, i_17, i_18, i_19, i_20, i_21, i_22,
            i_23, i_24, i_25, i_26, i_27, i_28, i_29, i_30, i_31, i_32, i_33,
            i_34, i_35, i_36, i_37, i_38, i_39, i_40, i_41, i_42, i_43, i_44,
            i_45, i_46, i_47, i_48, i_49, i_50, i_51, i_52, i_53, i_54, i_55,
            i_56, i_57, i_58, i_59, i_60, i_61, i_62, i_63, i_64, i_65, i_66,
            i_67, i_68, i_69, i_70, i_71, i_72, i_73, i_74, i_75, i_76, i_77,
            i_78, i_79, i_80, i_81, i_82, i_83, i_84, i_85, i_86, i_87, i_88,
            i_89, i_90, i_91, i_92, i_93, i_94, i_95, i_96, i_97, i_98, i_99,
            i_100, i_101, i_102, i_103, i_104, i_105, i_106, i_107, i_108,
            i_109, i_110, i_111, i_112, i_113, i_114, i_115, i_116, i_117,
            i_118, i_119, i_120, i_121, i_122, i_123, i_124, i_125, i_126,
            i_127, i_128, i_129, i_130, i_131, i_132, i_133, i_134, i_135,
            i_136, i_137, i_138, i_139, i_140, i_141, i_142, i_143, i_144,
            i_145, i_146, i_147, i_148, i_149, i_150, i_151, i_152, i_153,
            i_154, i_155, i_156, i_157, i_158, i_159, i_160, i_161, i_162,
            i_163, i_164, i_165, i_166, i_167, i_168, i_169, i_170, i_171,
            i_172, i_173, i_174, i_175, i_176, i_177, i_178, i_179, i_180,
            i_181, i_182, i_183, i_184, i_185, i_186, i_187, i_188, i_189,
            i_190, i_191, i_192, i_193, i_194, i_195, i_196, i_197, i_198,
            i_199, i_200, i_201, i_202, i_203, i_204, i_205, i_206, i_207,
            i_208, i_209, i_210, i_211, i_212, i_213, i_214, i_215, i_216,
            i_217, i_218, i_219, i_220, i_221, i_222, i_223, i_224, i_225,
            i_226 = 1;
        })();
        """))
        standard = minify_print(tree, obfuscate=False)
        self.assertIn('i_10,i_11,i_12,i_13', standard)
        minified = minify_print(tree, obfuscate=True)
        # we cannot directly test the output due to the dict lookup not
        # being deterministic, however we can assure that the bracketing
        # names (dn and dp) are generated, and ensure that 'do' is not
        # present.
        self.assertIn('dn', minified)
        self.assertNotIn('do', minified)
        self.assertIn('dp', minified)


def parse_to_sourcemap_tokens_pretty(text):
    return quad(Unparser(rules=(
        default_rules,
        indent(),
    ))(parse(text, with_comments=True)))


def parse_to_sourcemap_tokens_min(text):
    return quad(Unparser(rules=(
        minimum_rules,
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
    ), (
        'assorted_comments',
        """
        // line
        /* block
           line 2
           final */
           // hrm
           this;
         /* more? */
        this;
        """, [
            ('// line', 1, 1, None),
            ('\n', 0, 0, None),
            ('/* block\n   line 2\n   final */', 2, 1, None),
            ('\n', 0, 0, None),
            ('// hrm', 5, 4, None),
            ('\n', 0, 0, None),
            ('this', 6, 4, None),
            (';', 6, 8, None),
            ('\n', 0, 0, None),
            ('/* more? */', 7, 2, None),
            ('\n', 0, 0, None),
            ('this', 8, 1, None),
            (';', 8, 5, None),
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


ES5IdentityTestCase = build_equality_testcase(
    'ES5IdentityTestCase', es5.pretty_print, ((
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
        r"""
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
        r"""
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
        function foo() {
          i++;
          i--;
          ++i;
          --i;
          !i;
        }
        """,

    ), (
        'shift_ops',
        """
        x << y;
        y >> x;
        function foo() {
          x << y;
          y >> x;
        }
        """,

    ), (
        'mul_ops',
        """
        x * y;
        y / x;
        x % z;
        function foo() {
          x * y;
          y / x;
          x % z;
        }
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
        (function(arg) {
        });
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
    ), (
        'line_continuation_string',
        r"""
        {
          var a = "\
          ";
        }
        """,
    ), (
        'var_non_word_char_separation',
        """
        var $foo = bar;
        """,
    )]))
)


PrintWithCommentsTestCase = build_equality_testcase(
    'PrintWithCommentsTestCase', pretty_print, ((
        label, parse(value, with_comments=True), value,
    ) for label, value in ((
        label,
        # using lstrip as the pretty printer produces a trailing newline
        textwrap.dedent(value).lstrip(),
    ) for label, value in [(
        'this_keyword',
        """
        // foo
        // foo
        /* foo */
        this;
        """,
    ), (
        'before_function',
        """
        /* a comment */
        function foo() {
        }
        """,

    ), (
        'before_if',
        """
        /* a comment */
        if (foo == bar) {
        }
        """,

    ), (
        'not_quite_before_else_if',
        """
        if (somecondition) {
        }
        else /* a comment */
        if (foo == bar) {
          // also this is indented
          var baz = 1;
        }
        """,
    ), (
        'for_loop',
        """
        /* a comment */
        // more comments
        /* even more comments */
        for (i = 0; i < 10; i++) {
          var baz = 1;
        }
        """,
    ), (
        'while_loop',
        """
        /* an infinte loop */
        while (true) {
          // this is very pointless
          var baz = 1;
        }
        """,
    )]))
)


def parse_to_sourcemap_tokens_minify(text):
    return quad(minify_printer(obfuscate=True)(parse(text)))


ParsedNodeTypeSrcmapTokenMPTestCase = build_equality_testcase(
    'ParsedNodeTypeSrcmapTokenMPTestCase', parse_to_sourcemap_tokens_minify, ((
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
            ('=', 2, 9, None),
            ('5', 2, 11, None), (';', 2, 12, None),
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
            ('b', 3, 8, None), ('=', 3, 10, None),
            ('3', 3, 12, None), (';', 3, 13, None),
            ('var', 4, 1, None), (' ', 0, 0, None), ('a', 4, 5, None),
            ('=', 4, 7, None),
            ('1', 4, 9, None), (',', 0, 0, None),
            ('b', 4, 12, None), (';', 4, 13, None),
            ('var', 5, 1, None), (' ', 0, 0, None), ('a', 5, 5, None),
            ('=', 5, 7, None),
            ('5', 5, 9, None), (',', 0, 0, None),
            ('b', 5, 12, None), ('=', 5, 14, None),
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
            (';', 2, 1, None),
            (';', 3, 1, None),
        ],
    ), (
        'function_call_0',
        """
        test();
        """,
        [
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
    ), (
        'function_list',
        """
        (function main(root) {
          root.exports = [
            (function(module, exports) {
              module.exports = {};
            }),
            (function(module, exports) {
              exports.fun = 1;
            }),
          ];
        })(this);
        """, [
            ('(', 1, 1, None), ('function', 1, 2, None), (' ', 0, 0, None),
            ('main', 1, 11, None),
            ('(', 1, 15, None), ('a', 1, 16, 'root'), (')', 1, 20, None),
            ('{', 1, 22, None), ('a', 2, 3, 'root'), ('.', 2, 7, None),
            ('exports', 2, 8, None), ('=', 2, 16, None),
            ('[', 2, 18, None),
            ('(', 3, 5, None), ('function', 3, 6, None), ('(', 3, 14, None),
            ('a', 3, 15, 'module'), (',', 0, 0, None), ('b', 3, 23, 'exports'),
            (')', 3, 30, None), ('{', 3, 32, None),
            ('a', 4, 7, 'module'), ('.', 4, 13, None),
            ('exports', 4, 14, None), ('=', 4, 22, None), ('{', 4, 24, None),
            ('}', 4, 25, None), (';', 4, 26, None), ('}', 5, 5, None),
            (')', 5, 6, None),
            (',', 0, 0, None),
            ('(', 6, 5, None), ('function', 6, 6, None), ('(', 6, 14, None),
            ('b', 6, 15, 'module'), (',', 0, 0, None), ('a', 6, 23, 'exports'),
            (')', 6, 30, None), ('{', 6, 32, None),
            ('a', 7, 7, 'exports'), ('.', 7, 14, None),
            ('fun', 7, 15, None), ('=', 7, 19, None), ('1', 7, 21, None),
            (';', 7, 22, None), ('}', 8, 5, None), (')', 8, 6, None),
            (']', 9, 3, None), (';', 9, 4, None),
            ('}', 10, 1, None), (')', 10, 2, None),
            ('(', 10, 3, None), ('this', 10, 4, None), (')', 10, 8, None),
            (';', 10, 9, None),
        ],
    ), (
        'elision_function_list',
        """
        (function main(root) {
          root.exports = [
            (function(module, exports) {
              module.exports = {};
            }),,,,,,,
            (function(module, exports) {
              exports.fun = 1;
            }),,
          ];
        })(this);
        """, [
            ('(', 1, 1, None), ('function', 1, 2, None), (' ', 0, 0, None),
            ('main', 1, 11, None),
            ('(', 1, 15, None), ('a', 1, 16, 'root'), (')', 1, 20, None),
            ('{', 1, 22, None), ('a', 2, 3, 'root'), ('.', 2, 7, None),
            ('exports', 2, 8, None), ('=', 2, 16, None),
            ('[', 2, 18, None),
            ('(', 3, 5, None), ('function', 3, 6, None), ('(', 3, 14, None),
            ('a', 3, 15, 'module'), (',', 0, 0, None), ('b', 3, 23, 'exports'),
            (')', 3, 30, None), ('{', 3, 32, None),
            ('a', 4, 7, 'module'), ('.', 4, 13, None),
            ('exports', 4, 14, None), ('=', 4, 22, None), ('{', 4, 24, None),
            ('}', 4, 25, None), (';', 4, 26, None), ('}', 5, 5, None),
            (')', 5, 6, None),
            (',', 0, 0, None), (',,,,,,', 5, 8, None),
            ('(', 6, 5, None), ('function', 6, 6, None), ('(', 6, 14, None),
            ('b', 6, 15, 'module'), (',', 0, 0, None), ('a', 6, 23, 'exports'),
            (')', 6, 30, None), ('{', 6, 32, None),
            ('a', 7, 7, 'exports'), ('.', 7, 14, None),
            ('fun', 7, 15, None), ('=', 7, 19, None), ('1', 7, 21, None),
            (';', 7, 22, None), ('}', 8, 5, None), (')', 8, 6, None),
            (',', 0, 0, None), (',', 8, 8, None),
            (']', 9, 3, None), (';', 9, 4, None),
            ('}', 10, 1, None), (')', 10, 2, None),
            ('(', 10, 3, None), ('this', 10, 4, None), (')', 10, 8, None),
            (';', 10, 9, None),
        ],
    )])
)


MinifyPrintTestCase = build_equality_testcase(
    'MinifyPrintTestCase',
    partial(minify_print, obfuscate=True, shadow_funcname=True), ((
        label,
        parse(textwrap.dedent(source).strip()),
        answer,
    ) for label, source, answer in [(
        'switch_statement',
        """
        (function() {
          var result;
          switch (day_of_week) {
            case 6:
            case 7:
              result = 'Weekend';
              break;
            case 1:
              result = 'Monday';
              break;
            default:
              break;
          }
          return result
        })();
        """,
        "(function(){var a;switch(day_of_week){case 6:case 7:a='Weekend';"
        "break;case 1:a='Monday';break;default:break;}return a;})();",
    ), (
        'function_with_arguments',
        """
        function foo(x, y) {
          z = 10 + x;
          return x + y + z;
        }
        """,
        "function foo(a,b){z=10+a;return a+b+z;}",

    ), (
        'plus_plusplus_split',
        """
        var a = b+ ++c+d;
        """,
        "var a=b+ ++c+d;"
    ), (
        'minus_plusplus_join',
        """
        var a = b- ++c+d;
        """,
        "var a=b-++c+d;"
    ), (
        'object_props',
        """
        (function() {
          Name.prototype = {
            validated: function(key) {
              return token.get(key + this.last);
            },

            get fullName() {
              return this.first + ' ' + this.last;
            },

            set fullName(name) {
              var names = name.split(' ');
              this.first = names[0];
              this.last = names[1];
            }
          };
        })();
        """,
        "(function(){Name.prototype={validated:function(a){return token.get("
        "a+this.last);},get fullName(){return this.first+' '+this.last;},"
        "set fullName(b){var a=b.split(' ');this.first=a[0];this.last=a[1];}};"
        "})();"
    ), (
        'object_props_nonword',
        """
        (function() {
          Name.prototype = {
            get $dollar() {
              return this.money;
            },

            set $dollar(value) {
              this.money = value;
            }
          };
        })();
        """,
        "(function(){Name.prototype={get $dollar(){return this.money;},"
        "set $dollar(a){this.money=a;}};})();"
    ), (
        'try_catch_shadow',
        """
        (function() {
          var value = 1;
          try {
            console.log(value);
            throw Error('welp');
          }
          catch (value) {
            console.log(value);
          }
        })();
        """,
        "(function(){var a=1;try{console.log(a);throw Error('welp');}catch(a){"
        "console.log(a);}})();"
    ), (
        'for_in_a_block',
        """
        if (true) {
            for(;;);
        }
        """,
        'if(true){for(;;);}',
    ), (
        'function_dollar_sign',
        """
        (function $() {
          (function $() {
            var foo = 1;
          })()
        })();
        """,
        '(function $(){(function a(){var a=1;})();})();',
    ), (
        'line_continuation_string',
        r"""
        var a = "\
          ";
        """,
        'var a="  ";',
    ), (
        'var_non_word_char_separation',
        r"""
        var $foo = bar;
        """,
        'var $foo=bar;',
    ), (
        'return_string',
        """
        return"foo";
        """,
        'return"foo";'
    ), (
        'return_statement_negation',
        """
        return !1;
        """,
        'return!1;'
    ), (
        'return_nonword',
        """
        return $foo;
        """,
        'return $foo;'
    ), (
        'return_underscore',
        """
        return _;
        """,
        'return _;'
    ), (
        'dollar_instanceof_dollar',
        """
        foo$ instanceof $bar;
        """,
        'foo$ instanceof $bar;'
    ), (
        'while_loop_break_nonword_label',
        """
        while (1) {
          break $dollar;
        }
        """,
        'while(1){break $dollar;}',
    ), (
        'while_continue_nonword_label',
        """
        while (1) {
          continue $dollar;
        }
        """,
        'while(1){continue $dollar;}',
    ), (
        'iteration_in_nonword',
        """
        for (p in $obj) {
        }
        """,
        'for(p in $obj){}',
    ), (
        'iteration_in_nonword_pre',
        """
        for ($bling$ in $bling$bling$) {
        }
        """,
        'for($bling$ in $bling$bling$){}',
    ), (
        'iteration_in_str',
        """
        for ($bling$ in"bingbling") {
          console.log($bling$);
        }
        """,
        'for($bling$ in"bingbling"){console.log($bling$);}',
    ), (
        'case_various',
        """
        switch (foo) {
          case $dollar:
            break;
          case !1:
            break;
          case"foo":
            break;
        }
        """,
        'switch(foo){case $dollar:break;case!1:break;case"foo":break;}',
    ), (
        'throw_various',
        """
        throw $exc;
        throw!1;
        throw"exception";
        """,
        'throw $exc;throw!1;throw"exception";',
    ), (
        'new_nonword',
        """
        new $Money();
        """,
        'new $Money();',
    )])
)


def minify_drop_semi_helper(tree):
    result = minify_print(
        tree, obfuscate=True, shadow_funcname=True, drop_semi=True)
    # try to parse the result to ensure that it also is valid
    new_tree = es5(result)
    assert result == minify_print(
        new_tree, obfuscate=True, shadow_funcname=True, drop_semi=True)
    return result


MinifyDropSemiPrintTestCase = build_equality_testcase(
    'MinifyDropSemiPrintTestCase',
    minify_drop_semi_helper, ((
        label,
        parse(textwrap.dedent(source).strip()),
        answer,
    ) for label, source, answer in [(
        'switch_statement',
        """
        (function() {
          var result;
          switch (day_of_week) {
            case 6:
            case 7:
              result = 'Weekend';
              break;
            case 1:
              result = 'Monday';
              break;
            default:
              break;
          }
          return result
        })();
        """,
        "(function(){var a;switch(day_of_week){case 6:case 7:a='Weekend';"
        "break;case 1:a='Monday';break;default:break}return a})()",
    ), (
        'function_with_arguments',
        """
        function foo(x, y) {
          z = 10 + x;
          return x + y + z;
        }
        """,
        "function foo(a,b){z=10+a;return a+b+z}",

    ), (
        'plus_plusplus_split',
        """
        var a = b+ ++c+d;
        """,
        "var a=b+ ++c+d"
    ), (
        'minus_plusplus_join',
        """
        var a = b- ++c+d;
        """,
        "var a=b-++c+d"
    ), (
        'object_props',
        """
        (function() {
          Name.prototype = {
            validated: function(key) {
              return token.get(key + this.last);
            },

            get fullName() {
              return this.first + ' ' + this.last;
            },

            set fullName(name) {
              var names = name.split(' ');
              this.first = names[0];
              this.last = names[1];
            }
          };
        })();
        """,
        "(function(){Name.prototype={validated:function(a){return token.get("
        "a+this.last)},get fullName(){return this.first+' '+this.last},"
        "set fullName(b){var a=b.split(' ');this.first=a[0];this.last=a[1]}}"
        "})()"
    ), (
        'try_catch_shadow',
        """
        (function() {
          var value = 1;
          try {
            console.log(value);
            throw Error('welp');
          }
          catch (value) {
            console.log(value);
          }
        })();
        """,
        "(function(){var a=1;try{console.log(a);throw Error('welp')}catch(a){"
        "console.log(a)}})()"
    ), (
        'for_in_a_block',
        """
        if (true) {
            for(;;);
        }
        """,
        'if(true){for(;;);}',
    ), (
        'function_dollar_sign',
        """
        (function $() {
          (function $() {
            var foo = 1;
          })()
        })();
        """,
        '(function $(){(function a(){var a=1})()})()',
    ), (
        'nested_return_function',
        """
        v = function() {
            return function() {
                return function() {
                };
            };
        };
        """,
        'v=function(){return function(){return function(){}}}',
    )])
)
