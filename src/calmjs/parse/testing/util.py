# -*- coding: utf-8 -*-
import unittest


def build_equality_testcase(name, f, manifest):
    """
    A builder for a unittest TestCase class

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

    for label, argument, answer in manifest:
        method_name = 'test_' + label
        if method_name in attrs:
            raise ValueError('label "' + label + '" has been redefined')
        attrs[method_name] = create_test_method(argument, answer)

    return type(name, (unittest.TestCase,), attrs)
