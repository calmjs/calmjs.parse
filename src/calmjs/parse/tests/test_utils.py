# -*- coding: utf-8 -*-
import unittest
import tempfile
from os.path import join
from os.path import pardir
from os.path import sep

from collections import namedtuple
from calmjs.parse import utils


class UtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.old_dist = utils.ply_dist
        self.py_major = utils.py_major

    def tearDown(self):
        utils.ply_dist = self.old_dist
        utils.py_major = self.py_major

    def test_name_something(self):
        # a quick and dirty
        utils.ply_dist = namedtuple('Distribution', ['version'])('3.00')
        utils.py_major = 2
        lextab, yacctab = utils.generate_tab_names('some.package')
        self.assertEqual(lextab, 'some.lextab_package_py2_ply3_00')
        self.assertEqual(yacctab, 'some.yacctab_package_py2_ply3_00')

    def test_name_unknown(self):
        utils.ply_dist = None
        utils.py_major = 3
        lextab, yacctab = utils.generate_tab_names('some.package')
        self.assertEqual(lextab, 'some.lextab_package_py3_plyunknown')
        self.assertEqual(yacctab, 'some.yacctab_package_py3_plyunknown')

    def test_repr_compat(self):
        class fake_unicode(object):
            def __repr__(self):
                return "u'fake'"

        previous = utils.unicode
        self.addCleanup(setattr, utils, 'unicode', previous)

        utils.unicode = fake_unicode
        self.assertEqual("'fake'", utils.repr_compat(fake_unicode()))
        utils.unicode = None
        self.assertEqual("u'fake'", utils.repr_compat(fake_unicode()))


class FileNormTestCase(unittest.TestCase):

    def test_find_common_same_base_same_level(self):
        base = tempfile.mktemp()
        source = join(base, 'src', 'file.js')
        source_alt = join(base, 'src', 'alt', 'file.js')
        source_min = join(base, 'src', 'file.min.js')
        source_map = join(base, 'src', 'file.min.js.map')

        # for generation of sourceMappingURL comment in source_min
        self.assertEqual(
            'file.min.js.map', utils.normrelpath(source_min, source_map))
        # for pointing from source_map.source to the source
        self.assertEqual(
            'file.js', utils.normrelpath(source_map, source))
        # for pointing from source_map.source to the source_min
        self.assertEqual(
            'file.min.js', utils.normrelpath(source_map, source_min))

        self.assertEqual(
            join('alt', 'file.js'), utils.normrelpath(source_map, source_alt))

    def test_find_common_same_base_parents_common(self):
        base = tempfile.mktemp()
        source = join(base, 'src', 'file.js')
        source_min = join(base, 'build', 'file.min.js')
        source_map = join(base, 'build', 'file.min.js.map')

        # mapping from source_map to source
        self.assertEqual([pardir, 'src', 'file.js'], utils.normrelpath(
            source_map, source).split(sep))
        # for pointing from source_map.source to the source_min
        self.assertEqual('file.min.js', utils.normrelpath(
            source_map, source_min))

    def test_find_double_parent(self):
        base = tempfile.mktemp()
        root = join(base, 'file.js')
        nested = join(base, 'src', 'dir', 'blahfile.js')

        self.assertEqual([pardir, pardir, 'file.js'], utils.normrelpath(
            nested, root).split(sep))
        self.assertEqual(['src', 'dir', 'blahfile.js'], utils.normrelpath(
            root, nested).split(sep))

    def test_find_same_prefix(self):
        base = tempfile.mktemp()
        src = join(base, 'basesrc', 'source.js')
        tgt = join(base, 'basetgt', 'target.js')
        self.assertEqual([pardir, 'basetgt', 'target.js'], utils.normrelpath(
            src, tgt).split(sep))

    def test_relative_dirs_ignored(self):
        base = tempfile.mktemp()
        absolute = join(base, 'file.js')
        relative = join('somedir', 'file.js')

        self.assertEqual(relative, utils.normrelpath(absolute, relative))
        self.assertEqual(absolute, utils.normrelpath(relative, absolute))
