# -*- coding: utf-8 -*-
import unittest

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
