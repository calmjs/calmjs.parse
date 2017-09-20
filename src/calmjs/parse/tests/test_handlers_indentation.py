# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.ruletypes import (
    Indent,
    Dedent,
    Newline,
    OptionalNewline,
)
from calmjs.parse.handlers.indentation import indent
from calmjs.parse.unparsers.walker import Dispatcher


class IndentatorTestCase(unittest.TestCase):

    def test_indentation(self):
        # initialise a barebone dispatcher.
        dispatcher = Dispatcher({}, None, {}, {}, indent_str='<TAB>')
        layout = indent()()['layout_handlers']
        newline = ('\n', 0, 0, None, None)
        indent1 = ('<TAB>', None, None, None, None)
        indent2 = ('<TAB><TAB>', None, None, None, None)

        def run(rule, before=None):
            return layout[rule](dispatcher, None, before, None, None)

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

        layout = indent(indent_str='    ')()['layout_handlers']
        self.assertIsNone(run(Indent))
        self.assertEqual(list(run(Newline)), [
            newline, ('    ', None, None, None, None)])

        self.assertEqual(list(run(OptionalNewline, before='\n')), [])
