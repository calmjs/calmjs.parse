# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.ruletypes import Token
from calmjs.parse.ruletypes import Layout
from calmjs.parse.ruletypes import Deferred


class PPTypesTestCase(unittest.TestCase):
    """
    Tests for selected pretty print types.
    """

    def test_layout(self):
        Layout()

    def test_token(self):
        token = Token()
        self.assertTrue(callable(token))
        with self.assertRaises(NotImplementedError):
            token(None, None, None)

    def test_deferred(self):
        deferred = Deferred()
        self.assertTrue(callable(deferred))
        with self.assertRaises(NotImplementedError):
            deferred(None, None)
