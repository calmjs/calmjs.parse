# -*- coding: utf-8 -*-
import unittest

from logging import getLogger

from calmjs.parse.testing.util import build_equality_testcase
from calmjs.parse.testing.util import build_exception_testcase
from calmjs.parse.testing.util import setup_logger

from calmjs.parse.tests.parser import format_repr_program_type


def run(self):
    """
    A dummy run method.
    """


class BuilderEqualityTestCase(unittest.TestCase):

    def test_build_equality_testcase(self):
        DummyTestCase = build_equality_testcase('DummyTestCase', int, [
            ('str_to_int_pass', '1', 1),
            ('str_to_int_fail', '2', 1),
            ('str_to_int_exception', 'z', 1),
        ])
        DummyTestCase.runTest = run
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


class BuilderExceptionTestCase(unittest.TestCase):

    def test_build_exception_testcase(self):
        def demo(arg):
            if not arg.isdigit():
                raise ValueError(arg + ' not a number')

        FailTestCase = build_exception_testcase(
            'FailTestCase', demo, [
                ('str_to_int_fail1', 'hello', 'hello not a number'),
                ('str_to_int_fail2', 'goodbye', 'hello not a number'),
                ('str_to_int_fail3', '1', '1 not a number'),
                ('str_to_int_no_msg', 'hello', None),
            ],
            ValueError,
        )
        FailTestCase.runTest = run
        testcase = FailTestCase()

        # ValueError should have been caught.
        testcase.test_str_to_int_fail1()
        # no message check done.
        testcase.test_str_to_int_no_msg()

        # wrong exception message
        with self.assertRaises(AssertionError):
            testcase.test_str_to_int_fail2()

        # Naturally, the final test will not raise it.
        with self.assertRaises(AssertionError):
            testcase.test_str_to_int_fail3()


class SetupLoggerTestCase(unittest.TestCase):

    def test_build_exception_testcase(self):
        class DemoTestCase(unittest.TestCase):
            def runTest(self):
                """Dummy run method for PY2"""

        testcase = DemoTestCase()
        logger = getLogger('demo_test_case')
        original_level = logger.level
        original_handlers = len(logger.handlers)
        setup_logger(testcase, logger)
        self.assertNotEqual(original_level, logger.level)
        self.assertNotEqual(original_handlers, len(logger.handlers))
        testcase.doCleanups()
        self.assertEqual(original_level, logger.level)
        self.assertEqual(original_handlers, len(logger.handlers))


class ParserTestSetupTestCase(unittest.TestCase):

    def test_match(self):
        result = format_repr_program_type('foo', '<Program>', 'ES4Program')
        self.assertEqual(result, '<ES4Program>')

    def test_fail(self):
        with self.assertRaises(ValueError) as e:
            format_repr_program_type('foo', '<ES4Program>', 'ES4Program')

        self.assertEqual(
            e.exception.args[0], "repr test result for 'foo' did not start "
            "with generic '<Program', got: <ES4Program>"
        )

        with self.assertRaises(ValueError) as e:
            format_repr_program_type('foo', '<ES5Program>', 'ES4Program')

        self.assertEqual(
            e.exception.args[0], "repr test result for 'foo' did not start "
            "with generic '<Program', got: <ES5Program>"
        )
