# -*- coding: utf-8 -*-
import unittest
from textwrap import dedent

from calmjs.parse import es5
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.mangler import mangle


class ManglerTestCase(unittest.TestCase):

    def test_simple_manual(self):
        tree = es5(dedent("""
        (function(){
          var foo = 1;
          var bar = 2;
        })(this);
        """).strip())
        mangle_unparser = Unparser(rules=(
            mangle(),
        ))

        list(mangle_unparser(tree))
