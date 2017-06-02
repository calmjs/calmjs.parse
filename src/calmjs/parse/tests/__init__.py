import unittest
import doctest
from os.path import dirname


def make_suite():  # pragma: no cover
    from calmjs.parse import lexer
    from calmjs.parse.visitors import nodevisitor

    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(
        'calmjs.parse.tests', pattern='test_*.py',
        top_level_dir=dirname(__file__)
    )
    test_suite.addTest(doctest.DocTestSuite(
        lexer, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS))
    test_suite.addTest(doctest.DocTestSuite(
        nodevisitor,
        optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS))

    return test_suite
