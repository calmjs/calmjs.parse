# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import textwrap
import unittest

from calmjs.parse import walkers
from calmjs.parse import es5
from calmjs.parse.parsers.es5 import asttypes

repr_walker = walkers.ReprWalker()
walker = walkers.Walker()


class WalkerTestCase(unittest.TestCase):

    def test_not_node(self):
        with self.assertRaises(TypeError):
            list(walker.filter('not_a_node', lambda x: True))
        with self.assertRaises(TypeError):
            list(walker.walk('not_a_node'))


class ReprTestCase(unittest.TestCase):

    maxDiff = None

    def test_basic(self):
        result = repr_walker.walk(es5(textwrap.dedent("""
        var o = {
          a: 1,
          b: 2
        };
        """)), pos=True)
        self.assertEqual(
            result, "<ES5Program @2:1 ?children=[<VarStatement @2:1 "
            "?children=[<VarDecl @2:5 identifier=<Identifier @2:5 value='o'>, "
            "initializer=<Object @2:9 properties=[<Assign @3:4 left="
            "<PropIdentifier @3:3 value='a'>, op=':', right=<Number @3:6 "
            "value='1'>>, <Assign @4:4 left=<PropIdentifier @4:3 value='b'>, "
            "op=':', right=<Number @4:6 value='2'>>]>>]>]>"
        )

    def test_indented_omitted(self):
        result = repr_walker.walk(es5(textwrap.dedent("""
        var o = {
          a: 1,
          b: 2
        };
        """).strip()), indent=2, pos=True, omit=(
            'op', 'right', 'lexpos', 'colno', 'lineno', 'identifier'))
        self.assertEqual(textwrap.dedent("""
        <ES5Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 initializer=<Object @1:9 properties=[
              <Assign @2:4 left=<PropIdentifier @2:3 value='a'>>,
              <Assign @3:4 left=<PropIdentifier @3:3 value='b'>>
            ]>>
          ]>
        ]>
        """).strip(), result)

    def test_various_nested(self):
        result = repr_walker.walk(es5(textwrap.dedent("""
        var j = function(x) {
          return {
            a: 1,
            b: {
              c: 2,
              d: x
            }
          };
        }
        """).strip()), indent=2, pos=True, omit=(
            'op', 'lexpos', 'colno', 'lineno', 'left'))
        self.assertEqual(textwrap.dedent("""
        <ES5Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier @1:5 value='j'>, initializer=\
<FuncExpr @1:9 elements=[
              <Return @2:3 expr=<Object @2:10 properties=[
                <Assign @3:6 right=<Number @3:8 value='1'>>,
                <Assign @4:6 right=<Object @4:8 properties=[
                  <Assign @5:8 right=<Number @5:10 value='2'>>,
                  <Assign @6:8 right=<Identifier @6:10 value='x'>>
                ]>>
              ]>>
            ], identifier=None, parameters=[
              <Identifier @1:18 value='x'>
            ]>>
          ]>
        ]>
        """).strip(), result)

    def test_depth_0(self):
        result = repr_walker.walk(es5(textwrap.dedent("""
        var j = function(x) {
          return {
            a: 1,
            b: {
              c: 2,
              d: x
            }
          };
        }
        """).strip()), omit=(), depth=0, indent=2)
        self.assertEqual(textwrap.dedent("""
        <ES5Program ...>
        """).strip(), result)

    def test_depth_2(self):
        result = repr_walker.walk(es5(textwrap.dedent("""
        var j = function(x) {
          return {
            a: 1,
            b: {
              c: 2,
              d: x
            }
          };
        }
        """).strip()), omit=(
            'op', 'left', 'lexpos', 'identifier'), depth=2, indent=2)
        self.assertEqual(textwrap.dedent("""
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl ...>
          ], colno=1, lineno=1>
        ], colno=1, lineno=1>
        """).strip(), result)

    def test_depth_3(self):
        result = repr_walker.walk(es5(textwrap.dedent("""
        var j = function(x) {
          return {
            a: 1,
            b: {
              c: 2,
              d: x
            }
          };
        }
        """).strip()), omit=(
            'op', 'left', 'lexpos', 'identifier'), depth=4, indent=2)
        self.assertEqual(textwrap.dedent("""
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl colno=5, initializer=<FuncExpr colno=9, elements=[
              <Return ...>
            ], lineno=1, parameters=[
              <Identifier ...>
            ]>, lineno=1>
          ], colno=1, lineno=1>
        ], colno=1, lineno=1>
        """).strip(), result)

    def test_call(self):
        src = textwrap.dedent("""
        var j = {
          a: 1,
          b: {
            c: 2,
            d: x
          }
        };
        var k = 'hello world';
        var f = 'foobar';
        """).strip()
        result = repr_walker(es5(src))
        self.assertEqual(repr(es5(src)), result)

    def test_repr(self):
        result = repr(es5(textwrap.dedent("""
        var j = null;

          var  k = this;
        """).strip()))
        self.assertEqual(textwrap.dedent("""
        <ES5Program @1:1 ?children=[
          <VarStatement @1:1 ?children=[
            <VarDecl @1:5 identifier=<Identifier ...>, initializer=<Null ...>>
          ]>,
          <VarStatement @3:3 ?children=[
            <VarDecl @3:8 identifier=<Identifier ...>, initializer=<This ...>>
          ]>
        ]>
        """).strip(), result)

    def test_synthetic_node_default_repr(self):
        node = asttypes.Object(properties=[
            asttypes.Assign(
                left=asttypes.String(value='"foo"'),
                op=':',
                right=asttypes.String(value='"bar"'),
            ),
            asttypes.Assign(
                left=asttypes.String(value='"result"'),
                op=':',
                right=asttypes.Number(value='1'),
            ),
        ])
        # simple sanity test
        self.assertEqual(textwrap.dedent("""
        {
          "foo": "bar",
          "result": 1
        }
        """).strip(), str(node))
        self.assertEqual(
            repr_walker(node),
            "<Object @?:? properties=[\n"

            "  <Assign @?:? left=<String @?:? value='\"foo\"'>, op=':', "
            "right=<String @?:? value='\"bar\"'>>,\n"

            "  <Assign @?:? left=<String @?:? value='\"result\"'>, op=':', "
            "right=<Number @?:? value='1'>>\n"

            "]>"
        )
