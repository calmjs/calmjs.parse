# -*- coding: utf-8 -*-

import textwrap
import unittest

from calmjs.parse.visitors import generic
from calmjs.parse import es5

repr_visitor = generic.ReprVisitor()


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
