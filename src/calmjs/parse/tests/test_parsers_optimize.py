# -*- coding: utf-8 -*-

import unittest
import importlib
import os
import sys

from shutil import rmtree
from tempfile import mkdtemp
from types import ModuleType
from ply import lex
from calmjs.parse.parsers import optimize
from calmjs.parse.parsers import es5


class OptimizeTestCase(unittest.TestCase):

    def setUp(self):
        self.purged = []
        optimize.unlink = self.purged.append

    def tearDown(self):
        optimize.unlink = os.unlink
        optimize.import_module = importlib.import_module
        # undo whatever monkey patch that may have happened
        lex.open = open

    def test_verify_paths(self):
        tempdir = mkdtemp()
        self.addCleanup(rmtree, tempdir)

        # create fake module files
        modules = [os.path.join(tempdir, name) for name in (
            'foo.pyc', 'bar.pyc', 'foo.py')]

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

        def sentinel():
            called.append(True)

        fake_es5 = ModuleType('fake_es5')
        fake_es5.lextab = 'some_lextab'
        fake_es5.yacctab = 'some_yacctab'
        fake_es5.Parser = sentinel

        optimize.optimize_build(fake_es5)
        self.assertEqual(len(self.purged), 0)
        self.assertTrue(called)

    def test_optimize_first_build(self):
        optimize.reoptimize_all(True, first_build=True)
        # shouldn't have purged any modules
        self.assertEqual(len(self.purged), 0)
