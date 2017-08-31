# -*- coding: utf-8 -*-
import unittest
from textwrap import dedent

from calmjs.parse import es5
from calmjs.parse.asttypes import Node
from calmjs.parse.ruletypes import Resolve
from calmjs.parse.ruletypes import Space
from calmjs.parse.layout import rule_handler_noop
from calmjs.parse.layout import token_handler_str_default
from calmjs.parse.layout import layout_handler_space_minimum
from calmjs.parse.unparsers.base import Dispatcher
from calmjs.parse.unparsers.base import minimum_layout_handlers
from calmjs.parse.unparsers.walker import walk
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.mangler import Scope
from calmjs.parse.mangler import Shortener
from calmjs.parse.mangler import NameGenerator
from calmjs.parse.mangler import mangle

empty_set = set({})


class NameGeneratorTestCase(unittest.TestCase):

    def test_basic(self):
        ng = NameGenerator()
        self.assertEqual('a', next(ng))
        self.assertEqual('b', next(ng))

    def test_skip(self):
        ng = NameGenerator(['if'], 'if')
        self.assertEqual('i', next(ng))
        self.assertEqual('f', next(ng))
        self.assertEqual('ii', next(ng))
        # if is skipped
        self.assertEqual('fi', next(ng))
        self.assertEqual('ff', next(ng))
        self.assertEqual('iii', next(ng))

    def test_additional_skip(self):
        ng1 = NameGenerator(['if'], 'if')
        ng2 = ng1(['ii'])
        v = iter(ng2)
        self.assertEqual('i', next(v))
        self.assertEqual('f', next(v))
        # ii is skipped
        # if is skipped
        self.assertEqual('fi', next(v))


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
        scope.reference('foo')
        scope.reference('bar')
        self.assertEqual({'bar'}, scope.global_symbols)
        self.assertEqual(empty_set, scope.global_symbols_in_children)

    def test_resolve(self):
        scope = Scope(None)
        scope.remapped_symbols['foo'] = 'f'
        self.assertEqual('f', scope.resolve('foo'))
        self.assertEqual('bar', scope.resolve('bar'))

    def test_resolve_with_parent(self):
        root = Scope(None)
        root.remapped_symbols['root'] = 'r'
        root.remapped_symbols['name'] = 'root'
        child = root.nest(None)
        child.remapped_symbols['child'] = 'c'
        child.remapped_symbols['name'] = 'child'
        grandchild = child.nest(None)
        grandchild.remapped_symbols['grandchild'] = 'c'
        grandchild.remapped_symbols['name'] = 'grandchild'

        self.assertEqual('r', root.resolve('root'))
        self.assertEqual('root', root.resolve('name'))

        self.assertEqual('r', child.resolve('root'))
        self.assertEqual('child', child.resolve('name'))

        self.assertEqual('r', grandchild.resolve('root'))
        self.assertEqual('grandchild', grandchild.resolve('name'))

    def test_children_references(self):
        root = Scope(None)
        child1 = root.nest(None)
        grandchild1_1 = child1.nest(None)
        root.nest(None)  # child2
        child3 = root.nest(None)
        child3.nest(None)  # grandchild3_1
        grandchild3_2 = child3.nest(None)
        greatgrandchild3_2_1 = grandchild3_2.nest(None)

        self.assertEqual(empty_set, root.global_symbols_in_children)

        # one of the greatgrandchild make use of 'foo' without declaring
        # it.
        greatgrandchild3_2_1.reference('foo')
        self.assertEqual({'foo'}, root.global_symbols_in_children)
        self.assertEqual({'foo'}, child3.global_symbols_in_children)
        self.assertEqual(empty_set, child1.global_symbols_in_children)

        # some other grandchild does a few values, too
        grandchild1_1.reference('foo')
        self.assertEqual({'foo'}, child1.global_symbols_in_children)
        self.assertEqual({'foo'}, root.global_symbols_in_children)
        grandchild1_1.reference('a')
        self.assertEqual({'foo', 'a'}, child1.global_symbols_in_children)
        self.assertEqual({'foo', 'a'}, root.global_symbols_in_children)
        self.assertEqual({'foo'}, child3.global_symbols_in_children)

        # however, enough is enough, grandchild3_2 declares 'foo'
        grandchild3_2.declare('foo')
        # resulting in child3 no longer seeing that as referenced.
        self.assertEqual(empty_set, child3.global_symbols_in_children)
        # root still not immune as some other child still reference it.
        self.assertEqual({'foo', 'a'}, root.global_symbols_in_children)

    def test_close(self):
        root = Scope(None)
        root.reference('window')
        child = root.nest(None)
        child.reference('window')
        child.close()
        root.close()

        self.assertEqual({'window': 2}, root.referenced_symbols)
        self.assertEqual({'window': 1}, child.referenced_symbols)

        with self.assertRaises(ValueError):
            root.close()

        self.assertEqual({'window': 2}, root.referenced_symbols)

    def test_close_all_check_references(self):
        # for ease of counting everything
        root = Scope(None)
        child1 = root.nest(None)
        grandchild1_1 = child1.nest(None)
        child2 = root.nest(None)
        child3 = root.nest(None)
        child3.nest(None)  # grandchild3_1
        grandchild3_2 = child3.nest(None)
        greatgrandchild3_2_1 = grandchild3_2.nest(None)
        grandchild3_2.nest(None)  # greatgrandchild3_2_2
        child4 = root.nest(None)
        child5 = root.nest(None)

        greatgrandchild3_2_1.reference('window')
        greatgrandchild3_2_1.reference('window')
        grandchild3_2.reference('window')
        child3.declare('window')
        child3.reference('window')  # reference follows declare

        greatgrandchild3_2_1.reference('document')
        grandchild3_2.reference('document')

        child1.reference('window')
        grandchild1_1.reference('window')

        child2.reference('window')
        child2.reference('document')
        child2.declare('document')
        child2.reference('document')

        child4.reference('console')

        self.assertEqual({}, root.referenced_symbols)
        self.assertEqual({}, child5.referenced_symbols)
        root.close_all()
        self.assertEqual({
            'window': 3,
            'document': 2,
            'console': 1,
        }, root.referenced_symbols)
        self.assertEqual({
            'document': 2,
            'window': 1,
        }, child2.referenced_symbols)
        self.assertEqual({
            'document': 1,
            'window': 2,
        }, greatgrandchild3_2_1.referenced_symbols)
        self.assertEqual({
            'document': 2,
            'window': 3,
        }, grandchild3_2.referenced_symbols)

    def test_build_remap_symbols_parent_handling(self):
        # only after the final close is called.
        root = Scope(None)
        child1 = root.nest(None)
        child2 = root.nest(None)
        child3 = root.nest(None)
        grandchild2_1 = child2.nest(None)
        grandchild2_2 = child2.nest(None)
        grandchild2_3 = child2.nest(None)
        grandchild3_2 = child3.nest(None)
        greatgrandchild3_2_1 = grandchild3_2.nest(None)

        child3.declare('foo')
        child3.reference('foo')
        child2.declare('bar')
        child2.reference('bar')
        child2.reference('bar')  # to ensure this has priority
        child2.declare('foo')
        child2.reference('foo')
        # child1 does not declare fun
        child1.reference('fun')

        # first grandchild has declared and use foo, touches no
        # parents
        grandchild2_1.declare('foo')
        grandchild2_1.reference('foo')

        # the other grandchild declares new shadow, but also reference
        # a parent
        grandchild2_1.declare('bar')
        grandchild2_2.reference('bar')
        grandchild2_2.declare('custom')
        grandchild2_2.reference('custom')

        grandchild2_3.reference('foo')

        greatgrandchild3_2_1.declare('baz')
        greatgrandchild3_2_1.reference('window')
        root.declare('window')

        root.close_all()
        ng = NameGenerator()

        root.build_remap_symbols(ng)
        # root was ignored.
        self.assertEqual('window', root.resolve('window'))
        # these are independent.
        self.assertEqual('a', child3.resolve('foo'))
        self.assertEqual('a', child2.resolve('bar'))
        self.assertEqual('b', child2.resolve('foo'))

        # it never referenced no other variable
        self.assertEqual('a', grandchild2_1.resolve('foo'))
        # it has referenced bar, which was declared in parent ('a')
        self.assertEqual(child2.resolve('bar'), grandchild2_2.resolve('bar'))
        # naturally, its first declared variable is now 'b', shadows
        # over the remapped 'foo' which it doesn't use.
        self.assertEqual('b', grandchild2_2.resolve('custom'))

        # it will just get the foo fromchild2
        self.assertEqual('b', grandchild2_3.resolve('foo'))

        # this one was not remapped
        self.assertEqual('window', greatgrandchild3_2_1.resolve('window'))
        # remap the root node
        root.build_remap_symbols(ng, children_only=False)
        # this one was not remapped
        self.assertEqual('a', greatgrandchild3_2_1.resolve('window'))

    def test_build_remap_symbols_children_handling(self):
        ng = NameGenerator()
        root = Scope(None)
        child = root.nest(None)
        grandchild = child.nest(None)
        greatgrandchild = grandchild.nest(None)

        root.declare('bar')
        root.reference('bar')
        greatgrandchild.reference('a')

        root.build_remap_symbols(ng, children_only=False)
        # a was taken by greatgrandchild referencing that as an implicit
        # global.
        self.assertEqual('b', root.resolve('bar'))


class ManglerTestCase(unittest.TestCase):

    def test_simple_manual(self):
        tree = es5(dedent("""
        (function() {
          var foo = 1;
          var bar = 2;
          bar = 3;
        })(this);
        """).strip())
        mangle_unparser = Unparser(rules=(
            mangle(),
            minimum_layout_handlers,
        ))

        self.assertEqual(
            '(function(){var b=1;var a=2;a=3;})(this);',
            ''.join(c.text for c in mangle_unparser(tree)),
        )

    def test_no_resolve(self):
        # a simple test to show that a shortener without the initial
        # loading run executed (i.e. the one with the required handlers)
        # with the resolve added to the dispatcher will not crash, but
        # simply not have any effect.

        tree = es5(dedent("""
        (function() {
          var foo = 1;
          var bar = 2;
        })(this);
        """).strip())
        unparser = Unparser()
        shortener = Shortener()
        dispatcher = Dispatcher(
            unparser.definitions, token_handler_str_default, {
                Space: layout_handler_space_minimum,
            }, {
                Resolve: shortener.resolve,
            }
        )
        # see that the manually constructed minimum output works.
        self.assertEqual(
            "(function(){var foo=1;var bar=2;})(this);",
            ''.join(c.text for c in walk(dispatcher, tree))
        )

    def test_build_substitutions(self):
        tree = es5(dedent("""
        (function(root) {
          var foo = 1;
          var bar = 2;
          baz = 3;
          foo = 4;
          window.document.body.focus();
        })(this, factory);
        """).strip())
        unparser = Unparser()
        shortener = Shortener()
        # a bare dispatcher should work, as it is used for extracting
        # the definitions from.
        sub_dispatcher = Dispatcher(
            unparser.definitions, rule_handler_noop, {}, {})
        # only do the intial walk.
        result = shortener.walk(sub_dispatcher, tree)
        # should be empty list as the run should produce nothing, due to
        # the null token producer.
        self.assertEqual(result, [])

        # only one scope was defined.
        self.assertEqual(1, len(shortener.scopes))
        self.assertEqual(1, len(shortener.global_scope.children))

        # do some validation on the scope itself.
        self.assertEqual(set(), shortener.global_scope.declared_symbols)
        self.assertEqual(
            {'factory': 1}, shortener.global_scope.referenced_symbols)
        scope = shortener.global_scope.children[0]

        self.assertEqual({'root', 'foo', 'bar'}, scope.declared_symbols)
        self.assertEqual({
            'root': 1,
            'foo': 2,
            'bar': 1,
            'baz': 1,
            'window': 1,
        }, scope.referenced_symbols)

        # do a trial run to show that the resolution works.
        main_dispatcher = Dispatcher(
            unparser.definitions, token_handler_str_default, {
                Space: layout_handler_space_minimum,
            }, {
                Resolve: shortener.resolve,
            }
        )
        # see that the manually constructed minimum output works.
        self.assertEqual(
            "(function(root){var foo=1;var bar=2;baz=3;foo=4;"
            "window.document.body.focus();})(this,factory);",
            ''.join(c.text for c in walk(main_dispatcher, tree))
        )

        # now manually give the scope with a set of replacement names
        scope.remapped_symbols.update({
            'root': 'r',
            'foo': 'f',
            'bar': 'b',
            'baz': 'z',
        })
        self.assertEqual(
            "(function(r){var f=1;var b=2;z=3;f=4;"
            "window.document.body.focus();})(this,factory);",
            ''.join(c.text for c in walk(main_dispatcher, tree))
        )
