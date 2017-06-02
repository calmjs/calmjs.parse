# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.testing.util import build_equality_testcase


class BuilderTestCase(unittest.TestCase):

    def test_build_equality_testcase(self):
        DummyTestCase = build_equality_testcase('DummyTestCase', int, [
            ('str_to_int_pass', '1', 1),
            ('str_to_int_fail', '2', 1),
            ('str_to_int_exception', 'z', 1),
        ])
        testcase = DummyTestCase()
        testcase.test_str_to_int_pass()

        with self.assertRaises(AssertionError):
            testcase.test_str_to_int_fail()

        with self.assertRaises(ValueError):
            testcase.test_str_to_int_exception()

    def test_build_equality_testcase_flag_dupe_labels(self):
        with self.assertRaises(ValueError):
            build_equality_testcase('DummyTestCase', int, [
                ('str_to_int_dupe', '1', 1),
                ('str_to_int_dupe', '2', 2),
            ])
