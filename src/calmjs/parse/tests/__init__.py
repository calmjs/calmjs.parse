import unittest
import doctest
from os.path import dirname


def make_suite():  # pragma: no cover
    from calmjs.parse.lexers import es5 as es5lexer
    from calmjs.parse.visitors import generic

    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(
        'calmjs.parse.tests', pattern='test_*.py',
        top_level_dir=dirname(__file__)
    )
    test_suite.addTest(doctest.DocTestSuite(
        es5lexer, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS))
    test_suite.addTest(doctest.DocTestSuite(
        generic,
        optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS))

    return test_suite
