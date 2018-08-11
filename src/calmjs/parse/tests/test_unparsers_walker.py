# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from collections import namedtuple

from calmjs.parse.parsers.es5 import parse as es5
from calmjs.parse.asttypes import Node
from calmjs.parse.asttypes import VarStatement
from calmjs.parse.asttypes import VarDecl
from calmjs.parse.unparsers.walker import Dispatcher
from calmjs.parse.unparsers.walker import walk
from calmjs.parse.ruletypes import (
    Attr,
    JoinAttr,
    Text,
    Operator,
    Space,
    Newline,
    Iter,
    Declare,
    Resolve,
)

SimpleChunk = namedtuple('SimpleChunk', ['text'])
children_newline = JoinAttr(Iter(), value=(Newline,))
children_comma = JoinAttr(Iter(), value=(Text(value=','), Space,))


def setup_handlers(testcase):
    # only provide the bare minimum needed for the tests here.
    testcase.replacement = {}
    testcase.tokens_handled = []
    testcase.layouts_handled = []
    declared_vars = []

    def replace(dispatcher, node):
        return testcase.replacement.get(node.value, node.value)

    def declare(dispatcher, node):
        declared_vars.append(node.value)

    def simple_token_maker(
            token, dispatcher, node, subnode, sourcepath_stack=None):
        testcase.tokens_handled.append((token, dispatcher, node, subnode,))
        yield SimpleChunk(subnode)

    def simple_layout_space(dispatcher, node, before, after, prev):
        testcase.layouts_handled.append(
            (dispatcher, node, before, after, prev))
        # note that layouts must be yielded.
        yield SimpleChunk(' ')

    # return token_handler, layout_handlers for Dispatcher init
    return (
        simple_token_maker, {
            Space: simple_layout_space,
        }, {
            Declare: declare,
            Resolve: replace,
        },
        declared_vars,
    )


class DispatcherWalkTestCase(unittest.TestCase):

    def setup_defaults(self):
        # provide just enough of the everything that is required.
        token_handler, layout_handlers, deferrable_handlers, declared_vars = (
            setup_handlers(self))
        self.dispatcher = Dispatcher(
            definitions={
                'ES5Program': (children_newline, Newline,),
                'VarStatement': (
                    Text(value='var'), Space, children_comma, Text(value=';'),
                ),
                'VarDecl': (
                    Attr(Declare('identifier')),
                    Space, Operator(value='='), Space,
                    Attr('initializer'),
                ),
                'Identifier': (Attr(Resolve()),),
                'PropIdentifier': (Attr('value'),),
                'Number': (Attr('value'),),
                'DotAccessor': (
                    Attr('node'), Text(value='.'), Attr('identifier'),
                ),
                'FunctionCall': (
                    Attr('identifier'), Attr('args'),
                ),
                'Arguments': (
                    Text(value='('),
                    JoinAttr('items', value=(Text(value=','), Space)),
                    Text(value=')'),
                ),
            },
            token_handler=token_handler,
            layout_handlers=layout_handlers,
            deferrable_handlers=deferrable_handlers,
        )
        self.declared_vars = declared_vars

    def test_layouts_buffering(self):
        self.setup_defaults()
        # The buffered layout rule handler should be invoked with the
        # Node that originally queued the LayoutRuleChunk (rather, the
        # walk should have done that for the Node).
        original = 'var a = 1;'
        tree = es5(original)
        recreated = ''.join(c.text for c in walk(self.dispatcher, tree))
        # see that this at least works as expected
        self.assertEqual(original, recreated)
        # ensure that the 3 spaces have been handled as expected
        self.assertEqual(len(self.layouts_handled), 3)
        # the first Space should be derived from VarStatement
        self.assertTrue(isinstance(self.layouts_handled[0][1], VarStatement))
        # last two are in VarDecl
        self.assertTrue(isinstance(self.layouts_handled[1][1], VarDecl))
        self.assertTrue(isinstance(self.layouts_handled[2][1], VarDecl))
        self.assertEqual(['a'], self.declared_vars)

    def test_deferrable_resolve(self):
        self.setup_defaults()
        # define the replacement in the map that was set up.
        self.replacement['$'] = 'jq'
        tree = es5('var w = $(window).width();')
        recreated = ''.join(c.text for c in walk(self.dispatcher, tree))
        self.assertEqual('var w = jq(window).width();', recreated)
        self.assertEqual(['w'], self.declared_vars)

    def test_bad_definition_rule(self):
        (token_handler, layout_handlers, deferrable_handlers,
            self.declared_vars) = setup_handlers(self)
        with self.assertRaises(TypeError) as e:
            Dispatcher(
                definitions={'Node': (object(),)},
                token_handler=token_handler,
                layout_handlers=layout_handlers,
                deferrable_handlers=deferrable_handlers,
            )

        self.assertIn(
            "definition for 'Node' contain unsupported rule (got:",
            e.exception.args[0],
        )

    def test_nested_layouts(self):
        def simple_layout_space(dispatcher, node, before, after, prev):
            yield SimpleChunk(' ')

        def nested_layout(dispatcher, node, before, after, prev):
            yield SimpleChunk('?')

        def noop(*a, **kw):
            return
            yield  # pragma: no cover

        dispatcher = Dispatcher(
            definitions={
                'Node': (Space, JoinAttr(Iter(), value=(Space,)),)
            },
            token_handler=noop,
            layout_handlers={
                Space: simple_layout_space,
                (Space, Space): noop,
                ((Space, Space), Space): nested_layout,
            },
            deferrable_handlers={},
        )

        n0 = Node([])
        self.assertEqual(' ', ''.join(c.text for c in walk(dispatcher, n0)))
        n1 = Node([n0])
        self.assertEqual('', ''.join(c.text for c in walk(dispatcher, n1)))
        n2 = Node([n1, n0])
        self.assertEqual('?', ''.join(c.text for c in walk(dispatcher, n2)))

    def test_repeated_layouts(self):
        class Block(Node):
            pass

        def space_layout(dispatcher, node, before, after, prev):
            yield SimpleChunk(' ')

        def newline_layout(dispatcher, node, before, after, prev):
            yield SimpleChunk('n')

        dispatcher = Dispatcher(
            definitions={
                'Node': (Space,),
                'Block': (JoinAttr(Iter(), value=(Newline,)),)
            },
            token_handler=None,  # not actually produced
            layout_handlers={
                Space: space_layout,
                Newline: newline_layout,
                # drop the subsequent space
                (Newline, Space): newline_layout,
            },
            deferrable_handlers={},
        )

        n0 = Block([])
        self.assertEqual('', ''.join(c.text for c in walk(dispatcher, n0)))
        n1 = Block([Node([])] * 1)
        self.assertEqual(' ', ''.join(c.text for c in walk(dispatcher, n1)))
        n2 = Block([Node([])] * 2)
        self.assertEqual(' n', ''.join(c.text for c in walk(dispatcher, n2)))
        n3 = Block([Node([])] * 3)
        self.assertEqual(' nn', ''.join(c.text for c in walk(dispatcher, n3)))


class DispatcherTestcase(unittest.TestCase):

    def test_empty(self):
        dispatcher = Dispatcher({}, {}, {}, {})
        self.assertEqual(dict(dispatcher), {})

    def test_clone_definitions(self):
        marker = tuple()
        dispatcher = Dispatcher({'Node': marker}, {}, {}, {})
        self.assertEqual(dict(dispatcher), {'Node': marker})
