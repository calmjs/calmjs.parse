# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.asttypes import Node
from calmjs.parse.unparsers.base import BaseUnparser
from calmjs.parse.unparsers.walker import Dispatcher


class BaseUnparserTestCase(unittest.TestCase):

    def test_prewalk_fail(self):
        definitions = {}
        unparser = BaseUnparser(definitions)
        # can't lookup an empty definition
        with self.assertRaises(KeyError):
            self.assertEqual([], list(unparser(Node())))

    def test_minimum_definition(self):
        definitions = {'Node': ()}
        unparser = BaseUnparser(definitions)
        self.assertEqual([], list(unparser(Node())))

    def test_prewalk_hooking(self):
        results = {}

        def prewalk_dummy(dispatcher, node):
            results.update({'dispatcher': dispatcher, 'node': node})

        definitions = {'Node': ()}
        unparser = BaseUnparser(definitions, prewalk_hooks=[prewalk_dummy])
        self.assertEqual(results, {})
        # invoke complete run to trigger prewalk hook.
        root = Node()
        self.assertEqual([], list(unparser(root)))
        self.assertTrue(isinstance(results['dispatcher'], Dispatcher))
        self.assertTrue(results['node'], root)

    def test_called_prewalk_via_rules(self):
        results = {}

        def prewalk_dummy(dispatcher, node):
            results.update({'dispatcher': dispatcher, 'node': node})

        def rule():
            return {'prewalk_hooks': (prewalk_dummy,)}

        definitions = {'Node': ()}
        unparser = BaseUnparser(definitions, rules=(rule,))
        # invoke complete run to trigger prewalk hook.
        root = Node()
        self.assertEqual([], list(unparser(root)))
        self.assertTrue(isinstance(results['dispatcher'], Dispatcher))
        self.assertTrue(results['node'], root)
