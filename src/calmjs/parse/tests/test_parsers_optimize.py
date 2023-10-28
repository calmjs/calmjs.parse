# -*- coding: utf-8 -*-

import unittest
import importlib
import os
import sys

from io import StringIO
from shutil import rmtree
from tempfile import mkdtemp
from types import ModuleType
from ply import lex
from calmjs.parse.parsers import optimize
from calmjs.parse.parsers import es5
from calmjs.parse.utils import ply_dist


class OptimizeTestCase(unittest.TestCase):

    def setUp(self):
        self.purged = []
        optimize.unlink = self.purged.append

    def tearDown(self):
        optimize.unlink = os.unlink
        optimize.import_module = importlib.import_module
        optimize.ply_dist = ply_dist
        # undo whatever monkey patch that may have happened
        lex.open = open

    def break_ply(self):
        import ply

        def cleanup():
            sys.modules['ply'] = ply

        self.addCleanup(cleanup)
        sys.modules['ply'] = None

    def test_verify_paths(self):
        tempdir = mkdtemp()
        self.addCleanup(rmtree, tempdir)

        # create fake module files
        modules = [os.path.join(tempdir, name) for name in (
            'foo.pyc', 'bar.py', 'bar.pyc', 'foo.py')]

        for module in modules:
            with open(module, 'w'):
                pass

        self.assertEqual(
            sorted(modules),
            sorted(optimize.verify_paths(modules[:2])),
        )

    def test_find_tab_paths(self):
        fake_es5 = ModuleType('fake_es5')
        fake_es5.lextab = 'some_lextab'
        fake_es5.yacctab = 'some_yacctab'
        paths, missing = optimize.find_tab_paths(fake_es5)
        self.assertEqual([], paths)
        self.assertEqual(['some_lextab', 'some_yacctab'], missing)

        # ensure the parser exists
        es5.Parser()
        # should have created the optimized version of the file, if not
        # already exists
        answers = [
            sys.modules[es5.lextab].__file__,
            sys.modules[es5.yacctab].__file__,
        ]
        paths, missing = optimize.find_tab_paths(es5)
        self.assertEqual(paths, answers)
        self.assertEqual([], missing)

    def test_unlink_modules(self):
        es5.Parser()
        p = sys.modules[es5.yacctab].__file__
        self.assertTrue(os.path.exists(p))
        # unlink has been patched out
        optimize.purge_tabs(es5)
        self.assertNotIn(es5.yacctab, sys.modules)
        self.assertNotEqual(len(self.purged), 0)

    def test_not_imported(self):
        # mock the import failures
        def fail_import(module):
            raise ImportError()
        optimize.import_module = fail_import
        optimize.purge_tabs(es5)
        # since none are imported, no purges.
        self.assertEqual(len(self.purged), 0)

    def test_safeguard(self):
        fake_es5 = ModuleType('fake_es5')
        fake_es5.lextab = 'some_lextab'
        fake_es5.yacctab = 'some.system.module'

        with self.assertRaises(ValueError):
            optimize.purge_tabs(fake_es5)
        # since none are imported, no purges.
        self.assertEqual(len(self.purged), 0)

    def test_reoptimize(self):
        # this ensures everything is created
        optimize.reoptimize_all()
        # reset the purged list
        self.purged[:] = []
        # do the "real" run, should be twice the number of implemented
        # parsers.
        optimize.reoptimize_all()
        self.assertNotEqual(len(self.purged), 0)
        self.assertIs(lex.open, open)

    def test_reoptimize_monkey_patched(self):
        optimize.reoptimize_all(True)
        self.assertIsNot(lex.open, open)
        self.assertNotEqual(len(self.purged), 0)

    def test_optimize_build(self):
        called = []

        def sentinel(*a, **kw):
            called.append(True)

        fake_es5 = ModuleType('fake_namespace.fake_es5')
        fake_es5.Parser = sentinel

        # inject fake namespace and module
        sys.modules['fake_namespace'] = ModuleType('fake_namespace')
        self.addCleanup(sys.modules.pop, 'fake_namespace')
        sys.modules['fake_namespace.fake_es5'] = fake_es5
        self.addCleanup(sys.modules.pop, 'fake_namespace.fake_es5')

        optimize.optimize_build('fake_namespace.fake_es5')
        self.assertEqual(len(self.purged), 0)
        self.assertTrue(called)

    def test_optimize_first_build(self):
        optimize.reoptimize_all(True, first_build=True)
        # shouldn't have purged any modules
        self.assertEqual(len(self.purged), 0)

    def test_optimize_first_build_valid_with_broken_ply(self):
        self.break_ply()
        optimize.reoptimize_all(True, first_build=True)
        # shouldn't have purged any modules
        self.assertEqual(len(self.purged), 0)

    def test_assume_ply_version_default_ply(self):
        # only applicable if no ply_dist found
        optimize.ply_dist = None
        stderr = sys.stderr
        self.addCleanup(setattr, sys, 'stderr', stderr)

        # where ply is actually available; and since the real thing is
        # expected to be present and usable, intersperse that real value
        # into the expected string.
        import ply
        sys.stderr = StringIO()
        optimize._assume_ply_version()
        self.assertTrue(sys.stderr.getvalue().startswith(
            "WARNING: cannot find distribution for 'ply'; using value "
            "provided by ply, assuming 'ply==%s' for pre-generated modules" % (
                ply.__version__
            )))

    def test_assume_ply_version_override_ply(self):
        # can still override if ply is actually available
        optimize.ply_dist = None
        stderr = sys.stderr
        self.addCleanup(setattr, sys, 'stderr', stderr)

        self.addCleanup(os.environ.pop, optimize._ASSUME_ENVVAR, None)
        sys.stderr = StringIO()
        os.environ[optimize._ASSUME_ENVVAR] = '0.9999'  # should never exist
        optimize._assume_ply_version()
        self.assertTrue(sys.stderr.getvalue().startswith(
            "WARNING: cannot find distribution for 'ply'; using environment "
            "variable 'CALMJS_PARSE_ASSUME_PLY_VERSION', "
            "assuming 'ply==0.9999' for pre-generated modules"))

    def test_assume_ply_version_no_ply(self):
        # default when ply is fully broken.
        optimize.ply_dist = None
        stderr = sys.stderr
        self.addCleanup(setattr, sys, 'stderr', stderr)

        self.break_ply()
        sys.stderr = StringIO()
        optimize._assume_ply_version()
        self.assertTrue(sys.stderr.getvalue().startswith(
            "WARNING: cannot find distribution for 'ply'; using default "
            "value, assuming 'ply==3.11' for pre-generated modules"))

    def test_optimize_first_build_valid_with_broken_ply_error(self):
        def fail_import(*a, **kw):
            raise ImportError('no module named ply')

        optimize.import_module = fail_import

        with self.assertRaises(ImportError):
            optimize.reoptimize_all()

        stderr = sys.stderr

        def cleanup():
            sys.stderr = stderr

        self.addCleanup(cleanup)

        sys.stderr = StringIO()
        with self.assertRaises(SystemExit):
            optimize.reoptimize_all(first_build=True)

        self.assertTrue(sys.stderr.getvalue().startswith(
            "ERROR: cannot find pre-generated modules for the assumed 'ply' "
            "version"))

    def test_optimize_first_build_assume_broken_ply_error(self):
        optimize.ply_dist = None

        self.break_ply()

        def fail_import(*a, **kw):
            raise ImportError('no module named ply')

        optimize.import_module = fail_import

        with self.assertRaises(ImportError):
            optimize.reoptimize_all()

        stderr = sys.stderr

        def cleanup():
            sys.stderr = stderr

        self.addCleanup(cleanup)

        sys.stderr = StringIO()
        with self.assertRaises(SystemExit):
            optimize.reoptimize_all(first_build=True)

        lines = sys.stderr.getvalue().splitlines()
        self.assertTrue(lines[0].startswith(
            "WARNING: cannot find distribution for 'ply'; using default value"
            ))
        self.assertTrue(lines[1].startswith(
            "ERROR: cannot find pre-generated modules for the assumed 'ply' "
            "version"))

    def test_optimize_build_assume_broken_ply_but_available(self):
        optimize.ply_dist = None
        called = []

        def sentinel(*a, **kw):
            called.append(True)

        fake_es5 = ModuleType('fake_namespace.fake_es5')
        fake_es5.Parser = sentinel

        # inject fake namespace and module
        sys.modules['fake_namespace'] = ModuleType('fake_namespace')
        self.addCleanup(sys.modules.pop, 'fake_namespace')
        sys.modules['fake_namespace.fake_es5'] = fake_es5
        self.addCleanup(sys.modules.pop, 'fake_namespace.fake_es5')
        stderr = sys.stderr
        self.addCleanup(setattr, sys, 'stderr', stderr)
        sys.stderr = StringIO()

        optimize.optimize_build('fake_namespace.fake_es5')
        self.assertEqual(len(self.purged), 0)
        self.assertTrue(called)
        # this parser will not actually error as it does nothing; and
        # so not actually care whether ply actually available here or
        # not.
        self.assertTrue(sys.stderr.getvalue().startswith(
            "WARNING: cannot find distribution for 'ply'; "
            ))
        self.assertNotIn('ERROR', sys.stderr.getvalue())
