# -*- coding: utf-8 -*-

import textwrap
import unittest

from calmjs.parse.visitors import generic
from calmjs.parse import es5

repr_visitor = generic.ReprVisitor()
conditional = generic.ConditionalVisitor()


class ConditionalVisitorTestCase(unittest.TestCase):

    def test_not_node(self):
        with self.assertRaises(TypeError):
            list(conditional.generate('not_a_node', lambda x: True))


class ReprTestCase(unittest.TestCase):

    maxDiff = None

    def test_basic(self):
        result = repr_visitor.visit(es5(textwrap.dedent("""
        var o = {
          a: 1,
          b: 2
        };
        """)))
        self.assertEqual(
            result, "<ES5Program ?children=[<VarStatement "
            "?children=[<VarDecl identifier=<Identifier value='o'>, "
            "initializer=<Object properties=[<Assign left=<Identifier "
            "value='a'>, op=':', right=<Number value='1'>>, <Assign "
            "left=<Identifier value='b'>, op=':', "
            "right=<Number value='2'>>]>>]>]>"
        )

    def test_indented_omitted(self):
        result = repr_visitor.visit(es5(textwrap.dedent("""
        var o = {
          a: 1,
          b: 2
        };
        """).strip()), omit=('op', 'right', 'lexpos', 'identifier'), indent=2)
        self.assertEqual(textwrap.dedent("""
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl initializer=<Object properties=[
              <Assign left=<Identifier value='a'>>,
              <Assign left=<Identifier value='b'>>
            ]>, lineno=0>
          ], lineno=1>
        ], lineno=None>
        """).strip(), result)

    def test_various_nested(self):
        result = repr_visitor.visit(es5(textwrap.dedent("""
        var j = function(x) {
          return {
            a: 1,
            b: {
              c: 2,
              d: x
            }
          };
        }
        """).strip()), omit=('op', 'left', 'lexpos', 'identifier'), indent=2)
        self.assertEqual(textwrap.dedent("""
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl initializer=<FuncExpr elements=[
              <Return expr=<Object properties=[
                <Assign right=<Number value='1'>>,
                <Assign right=<Object properties=[
                  <Assign right=<Number value='2'>>,
                  <Assign right=<Identifier value='x'>>
                ]>>
              ]>>
            ], parameters=[
              <Identifier value='x'>
            ]>, lineno=0>
          ], lineno=1>
        ], lineno=None>
        """).strip(), result)

    def test_depth_0(self):
        result = repr_visitor.visit(es5(textwrap.dedent("""
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
            'op', 'left', 'lexpos', 'identifier'), depth=0, indent=2)
        self.assertEqual(textwrap.dedent("""
        <ES5Program ...>
        """).strip(), result)

    def test_depth_2(self):
        result = repr_visitor.visit(es5(textwrap.dedent("""
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
          ], lineno=1>
        ], lineno=None>
        """).strip(), result)

    def test_depth_3(self):
        result = repr_visitor.visit(es5(textwrap.dedent("""
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
            <VarDecl initializer=<FuncExpr elements=[
              <Return ...>
            ], parameters=[
              <Identifier ...>
            ]>, lineno=0>
          ], lineno=1>
        ], lineno=None>
        """).strip(), result)

    def test_call(self):
        result = repr_visitor(es5(textwrap.dedent("""
        var j = {
          a: 1,
          b: {
            c: 2,
            d: x
          }
        };
        var k = 'hello world';
        var f = 'foobar';
        """).strip()))
        self.assertEqual(textwrap.dedent("""
        <ES5Program ?children=[
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier ...>, initializer=<Object ...>>
          ]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier ...>, initializer=<String ...>>
          ]>,
          <VarStatement ?children=[
            <VarDecl identifier=<Identifier ...>, initializer=<String ...>>
          ]>
        ]>
        """).strip(), result)
