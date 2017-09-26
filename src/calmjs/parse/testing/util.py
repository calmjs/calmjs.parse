# -*- coding: utf-8 -*-
import unittest
import logging
from io import StringIO


def build_testcase(name, f, manifest, create_test_method, **default_attrs):

    attrs = {}
    attrs.update(default_attrs)

    for label, argument, answer in manifest:
        method_name = 'test_' + label
        if method_name in attrs:
            raise ValueError('label "' + label + '" has been redefined')
        attrs[method_name] = create_test_method(argument, answer)

    return type(str(name), (unittest.TestCase,), attrs)


def build_equality_testcase(name, f, manifest):
    """
    A builder for a unittest TestCase class that asserts equality

    name
        The name of the TestCase subclass that will be created
    f
        The function to be tested
    manifest
        An iterable of 3-tuples of strings, of:

        - label, will be used as name of created test method
        - argument to pass to function
        - the expected result.
    """

    def create_test_method(argument, answer):
        def _method(self):
            result = f(argument)
            self.assertEqual(answer, result)

        return _method

    attrs = {'maxDiff': None}
    return build_testcase(name, f, manifest, create_test_method, **attrs)


def build_exception_testcase(name, f, manifest, exception=None):
    """
    A builder for a unittest TestCase class that checks for a specific
    exception.

    name
        The name of the TestCase subclass that will be created
    f
        The function to be tested
    manifest
        An iterable of 2-tuples of strings, of:

        - label, will be used as name of created test method
        - argument to pass to function
    exception
        The exception expected to be raised.
    """

    def create_test_method(argument, msg):
        def _method(self):
            with self.assertRaises(exception) as e:
                f(argument)
            if msg is not None:
                self.assertEqual(msg, str(e.exception))

        return _method

    return build_testcase(name, f, manifest, create_test_method)


def setup_logger(testcase, logger, level=logging.DEBUG):
    testcase.addCleanup(logger.setLevel, logger.level)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(level)
    testcase.addCleanup(logger.removeHandler, handler)
    return stream
