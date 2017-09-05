# -*- coding: utf-8 -*-
import unittest
from inspect import getmembers
from inspect import isfunction

from calmjs.parse import rules


class BasicRulesTestCase(unittest.TestCase):

    def test_signature_conformance(self):
        # ensure that ALL functions defined in that module are rules
        # that conform to what is expected.
        for name, f in getmembers(rules, lambda item: (
                isfunction(item) and getattr(
                    item, '__module__', None) == rules.__name__)):
            self.assertTrue(isinstance(f()(), dict))
            self.assertIn(name, rules.__all__)
