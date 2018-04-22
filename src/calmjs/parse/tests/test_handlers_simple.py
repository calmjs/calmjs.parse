# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.asttypes import Node
from calmjs.parse.handlers.core import (
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,
    layout_handler_newline_optional_pretty,
    layout_handler_openbrace,
    layout_handler_closebrace,
    layout_handler_semicolon,
    deferrable_handler_literal_continuation,
)
from calmjs.parse.unparsers.walker import Dispatcher

empty = []
space = [(' ', 0, 0, None, None)]


class SimpleHandlersTestCase(unittest.TestCase):
    """
    Assorted test cases for edges.
    """

    def test_core_structures(self):
        # initialise a barebone dispatcher.
        node = Node()
        dispatcher = Dispatcher({}, None, {}, {})
        self.assertEqual([('{', 0, 0, None, None,)], list(
            layout_handler_openbrace(dispatcher, node, None, None, None)))
        self.assertEqual([('}', 0, 0, None, None,)], list(
            layout_handler_closebrace(dispatcher, node, None, None, None)))
        self.assertEqual([(';', 0, 0, None, None,)], list(
            layout_handler_semicolon(dispatcher, node, None, None, None)))

        # with token map
        node._token_map = {
            '{': [(0, 1, 1)],
            '}': [(1, 1, 2)],
            ';': [(2, 1, 3)],
        }
        self.assertEqual([('{', 1, 1, None, None,)], list(
            layout_handler_openbrace(dispatcher, node, None, None, None)))
        self.assertEqual([('}', 1, 2, None, None,)], list(
            layout_handler_closebrace(dispatcher, node, None, None, None)))
        self.assertEqual([(';', 1, 3, None, None,)], list(
            layout_handler_semicolon(dispatcher, node, None, None, None)))

    def test_space_optional_pretty(self):
        # initialise a barebone dispatcher.
        dispatcher = Dispatcher({}, None, {}, {})

        def run(a, b):
            return list(layout_handler_space_optional_pretty(
                # node and prev are not used.
                dispatcher, None, a, b, None))

        # also test out the cases where OptionalSpace was defined.
        self.assertEqual(run(None, None), empty)
        self.assertEqual(run('a', None), empty)
        self.assertEqual(run(None, 'a'), empty)
        # for Assign
        self.assertEqual(run('a', ':'), empty)
        self.assertEqual(run('a', '='), space)
        self.assertEqual(run('1', '='), space)

        self.assertEqual(run('a', '+='), space)
        self.assertEqual(run('a', '-='), space)
        self.assertEqual(run('a', '*='), space)
        self.assertEqual(run('a', '/='), space)
        self.assertEqual(run('a', '%='), space)
        self.assertEqual(run('a', '&='), space)
        self.assertEqual(run('a', '^='), space)
        self.assertEqual(run('a', '|='), space)
        self.assertEqual(run('a', '<<='), space)
        self.assertEqual(run('a', '>>='), space)
        self.assertEqual(run('a', '>>>='), space)

        # these rules are not defined, since they typically shouldn't
        # happen and that BinOp rules should use Space.
        self.assertEqual(run('+', 'a'), empty)
        self.assertEqual(run('-', 'a'), empty)
        self.assertEqual(run('*', 'a'), empty)
        self.assertEqual(run('/', 'a'), empty)

        # for Unary
        self.assertEqual(run('!', 'a'), empty)
        self.assertEqual(run('f', '1'), space)
        self.assertEqual(run('1', 'f'), space)
        self.assertEqual(run('f', '++'), empty)
        self.assertEqual(run('f', '--'), empty)
        self.assertEqual(run('--', 'f'), empty)
        self.assertEqual(run('++', 'f'), empty)
        self.assertEqual(run('+', '-'), empty)
        self.assertEqual(run('-', '+'), empty)
        self.assertEqual(run('-', '-'), space)
        self.assertEqual(run('+', '+'), space)

    def test_space_minimum(self):
        # initialise a barebone dispatcher.
        dispatcher = Dispatcher({}, None, {}, {})

        def run(a, b):
            return list(layout_handler_space_minimum(
                # node and prev are not used.
                dispatcher, None, a, b, None))

        self.assertEqual(run(None, None), empty)

        # for Assign
        self.assertEqual(run('a', ':'), empty)
        self.assertEqual(run('a', '='), empty)

        # for Unary
        self.assertEqual(run('!', 'a'), empty)
        self.assertEqual(run('f', '1'), space)
        self.assertEqual(run('1', 'f'), space)
        self.assertEqual(run('f', '+'), empty)
        self.assertEqual(run('f', '-'), empty)
        self.assertEqual(run('-', 'f'), empty)
        self.assertEqual(run('+', 'f'), empty)
        self.assertEqual(run('+', '-'), empty)
        self.assertEqual(run('-', '-'), space)
        self.assertEqual(run('+', '+'), space)
        self.assertEqual(run(',', 'y'), empty)
        self.assertEqual(run('1', ','), empty)

    def test_layout_handler_newline_optional_pretty(self):
        # yes using the lteral <CR><LF> is pretty hilarious, but just to
        # show that this is implemented to support whatever.
        dispatcher = Dispatcher({}, None, {}, {}, newline_str='<CR><LF>')
        newline = [('<CR><LF>', 0, 0, None, None)]

        def run(before, after, prev):
            return list(layout_handler_newline_optional_pretty(
                # node is not used.
                dispatcher, None, before, after, prev))

        # brand new empty program
        self.assertEqual(run(None, None, None), empty)
        # first line of a program
        self.assertEqual(run(None, 'function', None), empty)
        # previous token produced a newline
        self.assertEqual(run('\n', 'function', None), empty)
        # next token produced a newline
        self.assertEqual(run('}', '\n', None), empty)
        # Previous layout produced a newline
        self.assertEqual(run('}', '  ', '\n'), empty)

        # Previous layout produced a newline, with the custom str
        self.assertEqual(run('}', '  ', '<CR><LF>'), empty)

        # The first layout rule
        self.assertEqual(run(';', 'function', None), newline)

    def test_deferrable_handler_literal_continuation(self):
        dispatcher = Dispatcher({}, None, {}, {})
        node = Node()
        node.value = '"foo\\\r\nbar"'
        self.assertEqual('"foobar"', deferrable_handler_literal_continuation(
            dispatcher, node))
