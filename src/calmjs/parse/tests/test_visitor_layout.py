# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.visitors.layout import (
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,
)

empty = []
space = [(' ', 0, 0, None)]


class LayoutHandlerTestCase(unittest.TestCase):
    """
    Assorted test cases for edges.
    """

    def test_space_optional_pretty(self):
        def run(a, b):
            return list(layout_handler_space_optional_pretty(None, None, a, b))
        # first/second argument not used

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
            return list(layout_handler_space_minimum(None, None, a, b))

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
