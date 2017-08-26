# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.ruletypes import (
    Indent,
    Dedent,
    Newline,
    OptionalNewline,
)
from calmjs.parse.layout import (
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,
    layout_handler_newline_optional_pretty,
    indentation,
)
from calmjs.parse.unparsers.prettyprint import State

empty = []
space = [(' ', 0, 0, None)]


class LayoutHandlerTestCase(unittest.TestCase):
    """
    Assorted test cases for edges.
    """

    def test_space_optional_pretty(self):
        # initialise a barebone state.
        state = State({}, None, {})

        def run(a, b):
            return list(layout_handler_space_optional_pretty(
                # node and prev are not used.
                state, None, a, b, None))

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
        # initialise a barebone state.
        state = State({}, None, {})

        def run(a, b):
            return list(layout_handler_space_minimum(
                # node and prev are not used.
                state, None, a, b, None))

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
        state = State({}, None, {}, newline_str='<CR><LF>')
        newline = [('<CR><LF>', 0, 0, None)]

        def run(before, after, prev):
            return list(layout_handler_newline_optional_pretty(
                # node is not used.
                state, None, before, after, prev))

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

    def test_indentation(self):
        # initialise a barebone state.
        state = State({}, None, {}, indent_str='<TAB>')
        layout = indentation()()
        newline = ('\n', 0, 0, None)
        indent1 = ('<TAB>', None, None, None)
        indent2 = ('<TAB><TAB>', None, None, None)

        def run(rule, before=None):
            return layout[rule](state, None, before, None, None)

        self.assertEqual(list(run(Newline)), [newline])
        self.assertIsNone(run(Indent))
        self.assertEqual(list(run(Newline)), [newline, indent1])
        self.assertIsNone(run(Indent))
        self.assertEqual(list(run(Newline)), [newline, indent2])

        self.assertIsNone(run(Dedent))
        self.assertEqual(list(run(Newline)), [newline, indent1])
        self.assertIsNone(run(Dedent))
        self.assertEqual(list(run(Newline)), [newline])

        # negative shouldn't matter
        self.assertIsNone(run(Dedent))
        self.assertEqual(list(run(Newline)), [newline])
        # should move it back on the right track.
        self.assertIsNone(run(Indent))
        self.assertEqual(list(run(Newline)), [newline])

        layout = indentation(indent_str='    ')()
        self.assertIsNone(run(Indent))
        self.assertEqual(list(run(Newline)), [
            newline, ('    ', None, None, None)])

        self.assertEqual(list(run(OptionalNewline, before='\n')), [])
