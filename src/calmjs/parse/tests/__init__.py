import unittest
import doctest
from os.path import dirname
from pkg_resources import get_distribution


def make_suite():  # pragma: no cover
    from calmjs.parse.lexers import es5 as es5lexer
    from calmjs.parse import walkers
    from calmjs.parse import sourcemap

    parser = doctest.DocTestParser()
    optflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    pkgdesc = get_distribution('calmjs.parse').get_metadata('PKG-INFO')
    pkgdesc_tests = [
        t for t in parser.parse(pkgdesc) if isinstance(t, doctest.Example)]

    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(
        'calmjs.parse.tests', pattern='test_*.py',
        top_level_dir=dirname(__file__)
    )
    test_suite.addTest(doctest.DocTestSuite(es5lexer, optionflags=optflags))
    test_suite.addTest(doctest.DocTestSuite(walkers, optionflags=optflags))
    test_suite.addTest(doctest.DocTestSuite(sourcemap, optionflags=optflags))
    test_suite.addTest(doctest.DocTestCase(
        # skipping all the error case tests which should all be in the
        # troubleshooting section at the end; bump the index whenever
        # more failure examples are added.
        # also note that line number is unknown, as PKG_INFO has headers
        # and also the counter is somehow inaccurate in this case.
        doctest.DocTest(
            pkgdesc_tests[:-1], {}, 'PKG_INFO', 'README.rst', None, pkgdesc),
        optionflags=optflags,
    ))

    return test_suite
