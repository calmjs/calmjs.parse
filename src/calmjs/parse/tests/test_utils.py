# -*- coding: utf-8 -*-
import unittest

from collections import namedtuple
from calmjs.parse import utils


class UtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.old_dist = utils.ply_dist

    def tearDown(self):
        utils.ply_dist = self.old_dist

    def test_name_something(self):
        # a quick and dirty
        utils.ply_dist = namedtuple('Distribution', ['version'])('3.00')
        lextab, yacctab = utils.generate_tab_names('some.package')
        self.assertEqual(lextab, 'some.lextab_package_3_00')
        self.assertEqual(yacctab, 'some.yacctab_package_3_00')

    def test_name_unknown(self):
        utils.ply_dist = None
        lextab, yacctab = utils.generate_tab_names('some.package')
        self.assertEqual(lextab, 'some.lextab_package_unknown')
        self.assertEqual(yacctab, 'some.yacctab_package_unknown')
