# -*- coding: utf-8 -*-
import unittest
from textwrap import dedent

from calmjs.parse import es5
from calmjs.parse.asttypes import Node
from calmjs.parse.unparsers.base import Dispatcher
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.mangler import Scope
from calmjs.parse.mangler import Shortener
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

    def test_build_substitutions(self):
        tree = es5(dedent("""
        (function(){
          var foo = 1;
          var bar = 2;
          window.document.body.focus();
        })(this);
        """).strip())
        unparser = Unparser()
        shortener = Shortener()
        # a bare dispatcher should work, as it is used for extracting
        # the definitions from.
        dispatcher = Dispatcher(unparser.definitions, {}, {}, {})
        result = shortener.build_substitutions(dispatcher, tree)
        # should be empty list as the run should produce nothing, due to
        # the null token producer.
        self.assertEqual(result, [])

        # only one scope was defined.
        self.assertEqual(1, len(shortener.scopes))
        self.assertEqual(1, len(shortener.global_scope.children))

        # do some validation on the scope itself.
        scope = shortener.global_scope.children[0]

        self.assertEqual({'foo', 'bar'}, scope.declared_symbols)
