# -*- coding: utf-8 -*-
import unittest
from textwrap import dedent

from calmjs.parse import es5
from calmjs.parse.asttypes import Node
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.mangler import Scope
from calmjs.parse.mangler import mangle


class ScopeTestCase(unittest.TestCase):

    def test_scope_creation(self):
        scope = Scope(None)
        node = Node()
        scope.nest(node)
        self.assertEqual(scope.children[0].node, node)
        self.assertEqual(scope.children[0].parent, scope)

    def test_scope_symbols(self):
        scope = Scope(None)
        scope.declare('foo')
        scope.resolve('foo')
        scope.resolve('bar')
        self.assertEqual({'bar'}, scope.global_symbols)


class ManglerTestCase(unittest.TestCase):

    def test_simple_manual(self):
        tree = es5(dedent("""
        (function(){
          var foo = 1;
          var bar = 2;
        })(this);
        """).strip())
        mangle_unparser = Unparser(rules=(
            mangle(),
        ))

        list(mangle_unparser(tree))
