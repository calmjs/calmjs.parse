# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.asttypes import Identifier
from calmjs.parse.asttypes import String
from calmjs.parse.ruletypes import Declare
from calmjs.parse.ruletypes import Resolve
from calmjs.parse.ruletypes import Literal


class Node(object):
    """
    Just a dummy node type
    """


class DeferrableTestCase(unittest.TestCase):

    def setUp(self):
        self.handled = []

        def handler(dispatcher, node):
            self.handled.append({'dispatcher': dispatcher, 'node': node})
            return node.value.upper()

        class FakeDispatcher(object):
            def deferrable(fd, rule):
                return self.handler

        self.dispatcher = FakeDispatcher()
        self.handler = handler

    def test_declare_simple_not_implemented(self):
        node = Node()
        node.attr = Node()
        # no exception even on bad value when not provided a handler.
        self.handler = NotImplemented
        decl = Declare('attr')
        decl(self.dispatcher, node)

        # with a value value, nothing is handled if not implemented
        # either
        node.attr = Identifier('value')
        self.assertEqual(node.attr, decl(self.dispatcher, node))
        self.assertEqual([], self.handled)

    def test_declare_simple_various(self):
        node = Node()
        node.attr = Node()
        decl = Declare('attr')

        with self.assertRaises(TypeError) as e:
            decl(self.dispatcher, node)

        self.assertIn(
            "the resolved attribute 'attr' is not an Identifier",
            e.exception.args[0],
        )

        # try again with a proper identifier node
        node.attr = Identifier('value')
        result = decl(self.dispatcher, node)
        self.assertEqual(
            [{'dispatcher': self.dispatcher, 'node': node.attr}], self.handled)
        self.assertEqual(node.attr, result)

        # have attr not be defined.
        node.attr = None
        result = decl(self.dispatcher, node)
        # remained unchange.
        self.assertEqual(len(self.handled), 1)
        self.assertIsNone(result)

    def test_declare_list(self):
        node = Node()
        node.attr = [Identifier('value'), Node()]

        # no exception even on bad value when not provided a handler.
        decl = Declare('attr')
        handler, self.handler = self.handler, NotImplemented
        decl(self.dispatcher, node)

        # bring back the preset one
        self.handler = handler
        with self.assertRaises(TypeError) as e:
            decl(self.dispatcher, node)
        self.assertIn(
            "the resolved attribute 'attr[1]' is not an Identifier",
            e.exception.args[0],
        )
        # the first one will still be handled...
        self.assertEqual([
            {'dispatcher': self.dispatcher, 'node': node.attr[0]},
        ], self.handled)

        self.handled = []
        node.attr = [Identifier('value1'), Identifier('value2')]
        # should be handled in order.
        result = decl(self.dispatcher, node)
        self.assertEqual([
            {'dispatcher': self.dispatcher, 'node': node.attr[0]},
            {'dispatcher': self.dispatcher, 'node': node.attr[1]},
        ], self.handled)
        # result should still be the attr itself.
        self.assertEqual(node.attr, result)

    def test_resolve(self):
        node = Node()

        rslv = Resolve()
        with self.assertRaises(TypeError) as e:
            rslv(self.dispatcher, node)
        self.assertEqual(
            e.exception.args[0],
            'the Resolve Deferrable type only works with Identifier',
        )

        identifier = Identifier('value')
        self.assertEqual('VALUE', rslv(self.dispatcher, identifier))

        # if the handler is not implemented
        self.handler = NotImplemented
        self.assertEqual('value', rslv(self.dispatcher, identifier))

    def test_literal_string(self):
        literal = Literal()
        string = String('"value"')
        self.assertEqual('"VALUE"', literal(self.dispatcher, string))
        # if the handler is not implemented
        self.handler = NotImplemented
        self.assertEqual('"value"', literal(self.dispatcher, string))
