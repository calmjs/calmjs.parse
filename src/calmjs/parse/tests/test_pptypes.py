# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.ruletypes import Token
from calmjs.parse.ruletypes import Layout


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
