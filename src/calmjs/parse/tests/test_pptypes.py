# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.ruletypes import Token
from calmjs.parse.ruletypes import Layout
from calmjs.parse.ruletypes import Deferrable


class PPTypesTestCase(unittest.TestCase):
    """
    Tests for selected pretty print types.
    """

    def test_layout(self):
        Layout()

    def test_token(self):
        token = Token()
        self.assertTrue(callable(token))
        rule = token(None, None, None)
        with self.assertRaises(NotImplementedError):
            next(rule)

    def test_deferrable(self):
        deferrable = Deferrable()
        self.assertTrue(callable(deferrable))
        with self.assertRaises(NotImplementedError):
            deferrable(None, None)
