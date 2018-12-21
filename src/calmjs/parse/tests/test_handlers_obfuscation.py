# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from textwrap import dedent

from calmjs.parse import es5
from calmjs.parse.asttypes import Node
from calmjs.parse.asttypes import Identifier
from calmjs.parse.asttypes import Catch
from calmjs.parse.ruletypes import Attr
from calmjs.parse.ruletypes import Resolve
from calmjs.parse.ruletypes import Space
from calmjs.parse.ruletypes import RequiredSpace
from calmjs.parse.ruletypes import OpenBlock
from calmjs.parse.ruletypes import CloseBlock
from calmjs.parse.ruletypes import EndStatement

from calmjs.parse.unparsers.base import Dispatcher
from calmjs.parse.unparsers.walker import walk
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.handlers.indentation import indent
from calmjs.parse.handlers.core import rule_handler_noop
from calmjs.parse.handlers.core import token_handler_str_default
from calmjs.parse.handlers.core import layout_handler_space_minimum
from calmjs.parse.handlers.core import layout_handler_openbrace
from calmjs.parse.handlers.core import layout_handler_closebrace
from calmjs.parse.handlers.core import layout_handler_semicolon
from calmjs.parse.handlers.core import minimum_rules
from calmjs.parse.handlers.core import default_rules

from calmjs.parse.handlers.obfuscation import Scope
from calmjs.parse.handlers.obfuscation import CatchScope
from calmjs.parse.handlers.obfuscation import Obfuscator
from calmjs.parse.handlers.obfuscation import NameGenerator
from calmjs.parse.handlers.obfuscation import obfuscate
from calmjs.parse.handlers.obfuscation import token_handler_unobfuscate

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
        greatgrandchild.declare('baz')
        greatgrandchild.reference('baz')

        root.build_remap_symbols(ng, children_only=False)
        # 'a' was taken by greatgrandchild referencing that as an
        # implicit global, so root scope must not redeclare 'a'.
        self.assertEqual('b', root.resolve('bar'))
        # the greatgrandchild should also not turn 'baz' into 'a' for
        # the same reason.
        self.assertEqual('b', greatgrandchild.resolve('baz'))

    def test_build_remap_not_shadowed(self):
        ng = NameGenerator()
        d0 = Scope(None)
        d1 = d0.nest(None)
        d2 = d1.nest(None)
        d3 = d2.nest(None)
        d4 = d3.nest(None)
        d5 = d4.nest(None)

        d0.declare('root')
        d0.reference('root')
        d1.declare('d1')
        d1.reference('d1')
        d2.declare('d2')
        d2.reference('d2')
        d3.declare('d3')
        d3.reference('d3')
        d4.declare('d4')
        d4.reference('d4')
        d5.declare('d5')
        d5.reference('d5')
        # and the innermost descedent references root at d0.
        d5.reference('root')

        d0.build_remap_symbols(ng, children_only=False)
        self.assertEqual('a', d0.resolve('root'))
        self.assertEqual('a', d1.resolve('d1'))
        self.assertEqual('a', d2.resolve('d2'))
        self.assertEqual('a', d5.resolve('root'))
        self.assertEqual('b', d5.resolve('d5'))

    def test_catch_scope_basic(self):
        with self.assertRaises(TypeError) as e:
            CatchScope(None, None)
        self.assertEqual(
            e.exception.args[0], 'CatchScopes must have a Scope as a parent')

        parent = Scope(None)
        with self.assertRaises(AttributeError):
            # None isn't a node that can be resolved.
            CatchScope(None, parent)

        with self.assertRaises(AttributeError):
            # doesn't work with generic node either
            CatchScope(Node(), parent)

        catcher = CatchScope(Catch(Identifier('e'), []), parent)
        self.assertEqual(catcher.catch_symbol, 'e')
        catcher.close()

        with self.assertRaises(ValueError):
            catcher.close()

    def test_catch_scope_interactions(self):
        parent = Scope(None)
        parent.declare('local')
        parent.reference('local')
        catcher = parent.catchctx(Catch(Identifier('exc'), []))
        self.assertEqual(catcher.catch_symbol, 'exc')
        catcher.reference('exc')
        self.assertEqual(catcher.catch_symbol_usage, 1)

        catcher.declare('caught')
        catcher.reference('caught')
        catcher.reference('global')
        catcher.reference('local')
        self.assertEqual({'caught', 'local'}, parent.local_declared_symbols)
        self.assertEqual(
            {'caught': 1, 'global': 1, 'local': 2},
            parent.referenced_symbols)
        self.assertEqual(
            {'caught': 1, 'global': 1, 'local': 2, 'exc': 1},
            catcher.referenced_symbols)
        self.assertEqual(
            {'caught', 'local', 'exc'}, catcher.local_declared_symbols)

        catcher_child = catcher.funcdecl(None)
        catcher_child.reference('global')
        catcher_child.reference('local')
        catcher_child.reference('exc')
        self.assertEqual(
            {'global': 1, 'local': 1, 'exc': 1},
            catcher_child.leaked_referenced_symbols)

        # these should remain unchanged for now.
        self.assertEqual(
            {'caught': 1, 'global': 1, 'local': 2},
            parent.referenced_symbols)
        self.assertEqual(
            {'caught': 1, 'global': 1, 'local': 2, 'exc': 1},
            catcher.referenced_symbols)

        parent.close_all()
        # parent should inherit everything
        self.assertEqual(
            {'caught': 1, 'global': 2, 'local': 3},
            parent.referenced_symbols)
        self.assertEqual(
            {'caught': 1, 'global': 2, 'local': 3, 'exc': 2},
            catcher.referenced_symbols)

        # build the table and try some lookup
        parent.build_remap_symbols(NameGenerator, False)
        # should not resolve into anything, 'exc' is exclusive to the
        # catch context and not its parent.
        self.assertEqual('exc', parent.resolve('exc'))
        # local has been referenced the most, and generated first
        self.assertEqual('a', parent.resolve('local'))
        # parent should be able to resolve the 'caught' variable as it
        # was declared in the catch context which is mirrored onto its
        # actual context.
        self.assertEqual('b', parent.resolve('caught'))
        # should resolve into c, since it cannot shadow the remapped
        # global that is used by its children, or as a matter of fact,
        # its actual scope.
        self.assertEqual('c', catcher.resolve('exc'))
        self.assertEqual('b', catcher.resolve('caught'))
        self.assertEqual('a', catcher.resolve('local'))
        # the child will be resolving the same values its parent, the
        # catch context, sees.
        self.assertEqual('c', catcher_child.resolve('exc'))
        self.assertEqual('b', catcher_child.resolve('caught'))
        self.assertEqual('a', catcher_child.resolve('local'))


class ObfuscatorTestCase(unittest.TestCase):

    maxDiff = None

    def test_simple_manual(self):
        tree = es5(dedent("""
        (function() {
          var foo = 1;
          var bar = 2;
          bar = 3;
        })(this);
        """).strip())
        obfuscator_unparser = Unparser(rules=(
            minimum_rules,
            obfuscate(),
        ))

        self.assertEqual(
            '(function(){var b=1;var a=2;a=3;})(this);',
            ''.join(c.text for c in obfuscator_unparser(tree)),
        )

    def test_multiple_reuse(self):
        tree = es5(dedent("""
        (function() {
          var foo = 1;
          var bar = 2;
          bar = 3;
        })(this);
        """).strip())
        obfuscator_unparser = Unparser(rules=(
            minimum_rules,
            obfuscate(),
        ))

        self.assertEqual(
            ''.join(c.text for c in obfuscator_unparser(tree)),
            ''.join(c.text for c in obfuscator_unparser(tree)),
        )

    def test_no_resolve(self):
        # a simple test to show that an obfuscator without the initial
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
        obfuscator = Obfuscator()
        dispatcher = Dispatcher(
            unparser.definitions, token_handler_str_default, {
                Space: layout_handler_space_minimum,
                RequiredSpace: layout_handler_space_minimum,
                OpenBlock: layout_handler_openbrace,
                CloseBlock: layout_handler_closebrace,
                EndStatement: layout_handler_semicolon,
            }, {
                Resolve: obfuscator.resolve,
            }
        )
        # see that the manually constructed minimum output works.
        self.assertEqual(
            "(function(){var foo=1;var bar=2;})(this);",
            ''.join(c.text for c in walk(dispatcher, tree))
        )

    def test_token_handler_unobfuscate(self):
        # simple test to test the handler works
        node = Identifier('dummy')
        token = Attr('value', pos=None)
        # when nothing got remapped.
        self.assertEqual(('dummy', None, None, None, None), next(
            token_handler_unobfuscate(token, None, node, 'dummy')))
        # when the provided value differs
        self.assertEqual(('d', None, None, 'dummy', None), next(
            token_handler_unobfuscate(token, None, node, 'd')))

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
        obfuscator = Obfuscator()
        # a bare dispatcher should work, as it is used for extracting
        # the definitions from.
        sub_dispatcher = Dispatcher(
            unparser.definitions, rule_handler_noop, {}, {})
        # only do the intial walk.
        result = obfuscator.walk(sub_dispatcher, tree)
        # should be empty list as the run should produce nothing, due to
        # the null token producer.
        self.assertEqual(result, [])

        # only one scope was defined.
        self.assertEqual(1, len(obfuscator.scopes))
        self.assertEqual(1, len(obfuscator.global_scope.children))

        # do some validation on the scope itself.
        self.assertEqual(set(), obfuscator.global_scope.declared_symbols)
        self.assertEqual(
            {'factory': 1, 'baz': 1, 'window': 1},
            obfuscator.global_scope.referenced_symbols)
        scope = obfuscator.global_scope.children[0]

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
            unparser.definitions, token_handler_unobfuscate, {
                Space: layout_handler_space_minimum,
                RequiredSpace: layout_handler_space_minimum,
                OpenBlock: layout_handler_openbrace,
                CloseBlock: layout_handler_closebrace,
                EndStatement: layout_handler_semicolon,
            }, {
                Resolve: obfuscator.resolve,
            }
        )
        # see that the manually constructed minimum output works.
        self.assertEqual(
            "(function(root){var foo=1;var bar=2;baz=3;foo=4;"
            "window.document.body.focus();})(this,factory);",
            ''.join(c.text for c in walk(main_dispatcher, tree))
        )
        # since nothing was remapped.
        self.assertEqual([
        ], [
            (c.text, c.name) for c in walk(main_dispatcher, tree)
            if c.name
        ])

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
        # check that the source chunks yielded contain both the original
        # text token and the original row/col location
        self.assertEqual([
            ('r', 1, 11, 'root'),
            ('f', 2, 7, 'foo'),
            ('b', 3, 7, 'bar'),
            ('z', 4, 3, 'baz'),
            ('f', 5, 3, 'foo'),
        ], [c[:4] for c in walk(main_dispatcher, tree) if c.name])

    def test_obfuscate_globals(self):
        node = es5(dedent("""
        var a_global = 1;
        (function(a_param) {
          var a_local = 1;
          a_local = a_param;
          a_local = a_global;
        })();
        """).strip())

        self.assertEqual(dedent("""
        var a_global = 1;
        (function(b) {
            var a = 1;
            a = b;
            a = a_global;
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='    '),
            obfuscate(obfuscate_globals=False),
        ))(node)))

        self.assertEqual(dedent("""
        var a = 1;
        (function(c) {
            var b = 1;
            b = c;
            b = a;
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='    '),
            obfuscate(obfuscate_globals=True),
        ))(node)))

    def test_obfuscate_no_global_recursive(self):
        node = es5(dedent("""
        (function named(param1, param2) {
          param1 = param1 * param2 - param2;
          param2--;
          if (param2 < 0) {
            return named(param1, param2);
          }
          return param1;
        })();
        """).strip())

        self.assertEqual(dedent("""
        (function named(b, a) {
          b = b * a - a;
          a--;
          if (a < 0) {
            return named(b, a);
          }
          return b;
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(obfuscate_globals=False),
        ))(node)))

    def test_obfuscate_no_global_recursive_redeclared_shadow_funcname(self):
        node = es5(dedent("""
        (function $() {
          $();
          (function $() {
            var foo = 1;
          })();
        })();
        """).strip())

        self.assertEqual(dedent("""
        (function $() {
          a();
          (function a() {
            var a = 1;
          })();
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(obfuscate_globals=False, shadow_funcname=True),
        ))(node)))

    def test_obfuscate_no_global_recursive_redeclared_no_shadow_funcname(self):
        node = es5(dedent("""
        (function $() {
          $();
          (function $() {
            var foo = 1;
          })();
        })();
        """).strip())

        self.assertEqual(dedent("""
        (function $() {
          a();
          (function a() {
            var b = 1;
          })();
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(obfuscate_globals=False, shadow_funcname=False),
        ))(node)))

    def test_obfuscate_shadow_funcname_not_mapped(self):
        node = es5(dedent("""
        function a(arg) {
        }
        """).strip())

        self.assertEqual(dedent("""
        function a(a) {
        }
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(obfuscate_globals=False, shadow_funcname=True),
        ))(node)))

    def test_obfuscate_no_shadow_funcname_not_mapped(self):
        node = es5(dedent("""
        function a(arg) {
        }
        """).strip())

        self.assertEqual(dedent("""
        function a(b) {
        }
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(obfuscate_globals=False, shadow_funcname=False),
        ))(node)))

    def test_obfuscate_skip(self):
        node = es5(dedent("""
        (function(a_param) {
          var a_local = a_param;
        })();
        """).strip())

        self.assertEqual(dedent("""
        (function(c) {
            var d = c;
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='    '),
            obfuscate(reserved_keywords=('a', 'b',)),
        ))(node)))

    def test_no_shadow_children(self):
        node = es5(dedent("""
        var some_value = 1;
        (function(param) {
          a.is_not_declared_in_this_file(param);
        })();
        """).strip())

        self.assertEqual(dedent("""
        var b = 1;
        (function(b) {
            a.is_not_declared_in_this_file(b);
        })();
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='    '),
            obfuscate(obfuscate_globals=True),
        ))(node)))

    def test_no_shadow_parent_remapped(self):
        node = es5(dedent("""
        var a = c;
        (function(param) {
          b.is_not_declared_in_this_file(a, param);
        })(c);
        """).strip())

        # param can remap to c because the global 'c' not used in that
        # scope.
        self.assertEqual(dedent("""
        var a = c;
        (function(c) {
            b.is_not_declared_in_this_file(a, c);
        })(c);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='    '),
            obfuscate(obfuscate_globals=True),
        ))(node)))

    def test_multi_scope(self):
        node = es5(dedent("""
        (function(value) {
          var parent = 1;
          (function(value) {
            var child = 2;
            (function(value) {
              var grandchild = 3;
              (function(value) {
                var greatgrandchild = 4;
                (function(value) {
                  var result = 1;
                  // using greatgrandchild a lot to ensure priority
                  // mucking
                  console.log(parent);
                  console.log(greatgrandchild);
                  console.log(greatgrandchild * value);
                  console.log(greatgrandchild * parent);
                  console.log(greatgrandchild * greatgrandchild);
                })(value);
              })(value);
            })(value);
          })(value);
        })(0);
        """).strip())

        # Note that grandchild and greatgrandchild never had any of
        # their local variables referenced by any of their nested
        # scopes, their values got shadowed in the greatgrandchild scope
        # before both that and parent is used in the innermost scope.
        # Also, note that since greatgrandchild stopped propagating the
        # reference usage upwards, even though it has a lot more usage,
        # it never will claim priority over the parent at the parent
        # scope since parent got mapped to 'a' thus forcing
        # greatgrandchild to map to 'b', the next lowest value symbol.
        self.assertEqual(dedent("""
        (function(b) {
          var a = 1;
          (function(b) {
            var c = 2;
            (function(b) {
              var c = 3;
              (function(c) {
                var b = 4;
                (function(c) {
                  var d = 1;
                  console.log(a);
                  console.log(b);
                  console.log(b * c);
                  console.log(b * a);
                  console.log(b * b);
                })(c);
              })(b);
            })(b);
          })(b);
        })(0);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(),
        ))(node)))

    def test_obfuscate_try_catch_shadowed(self):
        node = es5(dedent("""
        var value = 1;
        try {
          console.log(value);
          throw Error("welp");
        }
        catch (value) {
          console.log(value);
        }
        """).strip())

        self.assertEqual(dedent("""
        var a = 1;
        try {
            console.log(a);
            throw Error("welp");
        }
        catch (a) {
            console.log(a);
        }
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='    '),
            obfuscate(obfuscate_globals=True),
        ))(node)))

    def test_obfuscate_try_catch_shadowed_scoped(self):
        node = es5(dedent("""
        var value = 100;
        (function() {
          var value = 1;
          try {
            console.log(value);
            throw Error("welp");
          }
          catch (value) {
            console.log(value);
          }
        })();
        console.log(value);
        """).strip())

        self.assertEqual(dedent("""
        var value = 100;
        (function() {
          var a = 1;
          try {
            console.log(a);
            throw Error("welp");
          }
          catch (a) {
            console.log(a);
          }
        })();
        console.log(value);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(),
        ))(node)))

    def test_obfuscate_try_catch_no_declare(self):
        node = es5(dedent("""
        var value = 100;
        (function() {
          value = 1;
          try {
            console.log(value);
            throw Error("welp");
          }
          catch (value) {
            value = 0;
            console.log(value);
          }
          console.log(value);
        })();
        console.log(value);
        """).strip())

        self.assertEqual(dedent("""
        var value = 100;
        (function() {
          value = 1;
          try {
            console.log(value);
            throw Error("welp");
          }
          catch (a) {
            a = 0;
            console.log(a);
          }
          console.log(value);
        })();
        console.log(value);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(),
        ))(node)))

    def test_obfuscate_try_catch_vardeclare_inside_catch(self):
        node = es5(dedent("""
        var value = 100;
        (function() {
          console.log(value);
          value = 1;
          try {
            console.log(value);
            throw Error("welp");
          }
          catch (exc) {
            var value = 2;
            console.log(value);
          }
          value = 3;
        })();
        console.log(value);
        """).strip())

        self.assertEqual(dedent("""
        var value = 100;
        (function() {
          console.log(a);
          a = 1;
          try {
            console.log(a);
            throw Error("welp");
          }
          catch (b) {
            var a = 2;
            console.log(a);
          }
          a = 3;
        })();
        console.log(value);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(),
        ))(node)))

    def test_obfuscate_try_catch_scope_inside_catch(self):
        node = es5(dedent("""
        var value = 100;
        (function() {
          var dummy = 0;
          console.log(value);
          value = 1;
          try {
            console.log(value);
            throw Error("welp");
          }
          catch (exc) {
            var value = 2;
            var welped = value;
            welped = 'welped';
            (function() {
              console.log(exc);
              console.log(value);
              console.log(welped);
            })();
          }
          value = 3;
        })();
        console.log(value);
        """).strip())

        # note that dummy -> c because exc is a local, not counted in
        # the priority at the parent scope.
        self.assertEqual(dedent("""
        var value = 100;
        (function() {
          var c = 0;
          console.log(a);
          a = 1;
          try {
            console.log(a);
            throw Error("welp");
          }
          catch (d) {
            var a = 2;
            var b = a;
            b = 'welped';
            (function() {
              console.log(d);
              console.log(a);
              console.log(b);
            })();
          }
          a = 3;
        })();
        console.log(value);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(),
        ))(node)))

    def test_functions_in_lists(self):
        node = es5(dedent("""
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
        """).strip())

        self.assertEqual(dedent("""
        (function main(a) {
          a.exports = [(function(a, b) {
            a.exports = {};
          }), (function(b, a) {
            a.fun = 1;
          })];
        })(this);
        """).lstrip(), ''.join(c.text for c in Unparser(rules=(
            default_rules,
            indent(indent_str='  '),
            obfuscate(),
        ))(node)))
