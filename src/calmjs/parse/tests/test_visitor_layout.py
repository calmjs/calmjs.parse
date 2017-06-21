# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.visitors.layout import (
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,
    layout_handler_newline_optional_pretty,
)

empty = []
space = [(' ', 0, 0, None)]
newline = [('\n', 0, 0, None)]


class LayoutHandlerTestCase(unittest.TestCase):
    """
    Assorted test cases for edges.
    """

    def test_space_optional_pretty(self):
        def run(a, b):
            return list(layout_handler_space_optional_pretty(
                # first/second and final argument not used
                None, None, a, b, None))

        # also test out the cases where OptionalSpace was defined.
        self.assertEqual(run(None, None), empty)
        # for Assign
        self.assertEqual(run('a', ':'), empty)
        self.assertEqual(run('a', '='), space)
        self.assertEqual(run('=', 'a'), space)
        self.assertEqual(run('1', '='), space)
        self.assertEqual(run('=', '1'), space)

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

    def test_space_minimum(self):
        def run(a, b):
            return list(layout_handler_space_minimum(
                # first/second and final argument not used
                None, None, a, b, None))

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
        def run(before, after, prev):
            return list(layout_handler_newline_optional_pretty(
                # first/second argument not used
                None, None, before, after, prev))

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

        # The first layout rule
        self.assertEqual(run(';', 'function', None), newline)
