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


class DeferredTestCase(unittest.TestCase):

    def test_declare(self):
        handled = {}

        def fake_dispatcher(thing):
            def handler(dispatcher, node):
                handled.update({'dispatcher': dispatcher, 'node': node})
            return handler

        node = Node()
        node.attr = Node()

        decl = Declare('attr')
        with self.assertRaises(TypeError):
            decl(fake_dispatcher, node)

        node.attr = Identifier('value')
        self.assertEqual(node.attr, decl(not_implemented, node))
        self.assertEqual({}, handled)

        result = decl(fake_dispatcher, node)
        self.assertEqual(
            {'dispatcher': fake_dispatcher, 'node': node.attr}, handled)
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
