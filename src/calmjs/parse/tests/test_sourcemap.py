# -*- coding: utf-8 -*-
import unittest

from calmjs.parse import sourcemap


class NameTestCase(unittest.TestCase):

    def test_name_update(self):
        names = sourcemap.Names()
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('world'), 1)
        self.assertEqual(names.update('world'), 0)
        self.assertEqual(names.update('hello'), -1)
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('goodbye'), 2)
        self.assertEqual(names.update('hello'), -2)
        self.assertEqual(names.update('goodbye'), 2)
        self.assertEqual(names.update('goodbye'), 0)
        self.assertEqual(names.update('goodbye'), 0)
        self.assertEqual(names.update('goodbye'), 0)
        self.assertEqual(names.update('world'), -1)
        self.assertEqual(names.update('person'), 2)
        self.assertEqual(names.update('people'), 1)
        self.assertEqual(names.update('people'), 0)
        self.assertEqual(names.update('hello'), -4)

        self.assertEqual(
            list(names), ['hello', 'world', 'goodbye', 'person', 'people'])
