# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.asttypes import Identifier
from calmjs.parse.ruletypes import Declare
from calmjs.parse.ruletypes import Resolve


def not_implemented(thing):
    return NotImplemented


class Node(object):
    """
    Just a dummy node type
    """


class DeferrableTestCase(unittest.TestCase):

    def test_declare_simple(self):
        handled = []

        def fake_dispatcher(thing):
            def handler(dispatcher, node):
                handled.append({'dispatcher': dispatcher, 'node': node})
            return handler

        node = Node()
        node.attr = Node()

        # no exception even on bad value when not provided a handler.
        decl = Declare('attr')
        decl(not_implemented, node)

        with self.assertRaises(TypeError) as e:
            decl(fake_dispatcher, node)
        self.assertIn(
            "the resolved attribute 'attr' is not an Identifier",
            e.exception.args[0],
        )

        # with a value value, nothing is handled if not implemented
        # either
        node.attr = Identifier('value')
        self.assertEqual(node.attr, decl(not_implemented, node))
        self.assertEqual([], handled)

        result = decl(fake_dispatcher, node)
        self.assertEqual(
            [{'dispatcher': fake_dispatcher, 'node': node.attr}], handled)
        self.assertEqual(node.attr, result)

        # have attr not be defined.
        node.attr = None
        result = decl(fake_dispatcher, node)
        # remained unchange.
        self.assertEqual(len(handled), 1)
        self.assertIsNone(result)

    def test_declare_list(self):
        handled = []

        def fake_dispatcher(thing):
            def handler(dispatcher, node):
                handled.append({'dispatcher': dispatcher, 'node': node})
            return handler

        node = Node()
        node.attr = [Identifier('value'), Node()]

        # no exception even on bad value when not provided a handler.
        decl = Declare('attr')
        decl(not_implemented, node)

        with self.assertRaises(TypeError) as e:
            decl(fake_dispatcher, node)
        self.assertIn(
            "the resolved attribute 'attr[1]' is not an Identifier",
            e.exception.args[0],
        )
        # the first one will still be handled...
        self.assertEqual([
            {'dispatcher': fake_dispatcher, 'node': node.attr[0]},
        ], handled)

        handled = []
        node.attr = [Identifier('value1'), Identifier('value2')]
        # should be handled in order.
        result = decl(fake_dispatcher, node)
        self.assertEqual([
            {'dispatcher': fake_dispatcher, 'node': node.attr[0]},
            {'dispatcher': fake_dispatcher, 'node': node.attr[1]},
        ], handled)
        # result should still be the attr itself.
        self.assertEqual(node.attr, result)

    def test_resolve(self):
        def fake_dispatcher(thing):
            def handler(dispatcher, node):
                return node.value.upper()
            return handler

        node = Node()

        rslv = Resolve()
        with self.assertRaises(TypeError):
            rslv(fake_dispatcher, node)

        identifier = Identifier('value')

        self.assertEqual('value', rslv(not_implemented, identifier))
        self.assertEqual('VALUE', rslv(fake_dispatcher, identifier))
