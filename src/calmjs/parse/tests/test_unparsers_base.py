# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from calmjs.parse.asttypes import Node
from calmjs.parse.unparsers.base import logger
from calmjs.parse.unparsers.base import BaseUnparser
from calmjs.parse.unparsers.walker import Dispatcher
from calmjs.parse.handlers.core import token_handler_str_default

from calmjs.parse.testing.util import setup_logger


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
            return node

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
            return node

        def rule():
            return {'prewalk_hooks': (prewalk_dummy,)}

        definitions = {'Node': ()}
        unparser = BaseUnparser(definitions, rules=(rule,))
        # invoke complete run to trigger prewalk hook.
        root = Node()
        self.assertEqual([], list(unparser(root)))
        self.assertTrue(isinstance(results['dispatcher'], Dispatcher))
        self.assertTrue(results['node'], root)

    def test_called_prewalk_multicall(self):
        prewalk = []

        def rule():
            prewalk.append(True)
            return {}

        root = Node()
        definitions = {'Node': ()}
        unparser = BaseUnparser(definitions, rules=(rule,))
        # invoke complete run to trigger prewalk hook.
        self.assertEqual(len(prewalk), 0)
        self.assertEqual([], list(unparser(root)))
        self.assertEqual(len(prewalk), 1)
        self.assertEqual([], list(unparser(root)))
        self.assertEqual(len(prewalk), 2)

    def test_token_handler_default(self):
        stream = setup_logger(self, logger)
        definitions = {}
        unparser = BaseUnparser(definitions)
        token_handler, layout_handlers, deferrable_handlers, prewalk_hooks = (
            unparser.setup())
        self.assertIs(token_handler, token_handler_str_default)
        self.assertIn(
            "DEBUG 'BaseUnparser' instance has no token_handler specified; "
            "default handler 'token_handler_str_default' activate",
            stream.getvalue())

    def test_token_handler_setup_manual(self):
        stream = setup_logger(self, logger)
        definitions = {}
        unparser = BaseUnparser(definitions, token_handler_str_default)
        token_handler, layout_handlers, deferrable_handlers, prewalk_hooks = (
            unparser.setup())
        self.assertIs(token_handler, token_handler_str_default)
        self.assertIn(
            "DEBUG 'BaseUnparser' instance using manually specified "
            "token_handler 'token_handler_str_default'", stream.getvalue()
        )

    def test_token_handler_setup_with_rules(self):
        def rule1():
            def handler1():
                "handler1"
            return {'token_handler': handler1}

        def rule2():
            def handler2():
                "handler2"
            return {'token_handler': handler2}

        def custom_handler():
            "custom handler"

        stream = setup_logger(self, logger)
        definitions = {}
        unparser = BaseUnparser(definitions, rules=(rule1, rule2))
        token_handler, layout_handlers, deferrable_handlers, prewalk_hooks = (
            unparser.setup())
        self.assertEqual(token_handler.__name__, 'handler2')

        self.assertIn(
            "DEBUG rule 'rule1' specified a token_handler 'handler1'",
            stream.getvalue()
        )
        self.assertIn(
            "WARNING rule 'rule2' specified a new token_handler 'handler2', "
            "overriding previously assigned token_handler 'handler1'",
            stream.getvalue()
        )

        unparser = BaseUnparser(
            definitions, token_handler=custom_handler, rules=(rule1, rule2))
        token_handler, layout_handlers, deferrable_handlers, prewalk_hooks = (
            unparser.setup())
        self.assertIs(token_handler, custom_handler)
        self.assertIn(
            "INFO manually specified token_handler 'custom_handler' to the "
            "'BaseUnparser' instance will override rule derived token_handler "
            "'handler2'",
            stream.getvalue()
        )
