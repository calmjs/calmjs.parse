# -*- coding: utf-8 -*-
import unittest

from calmjs.parse.asttypes import Comments
from calmjs.parse.asttypes import BlockComment
from calmjs.parse.asttypes import LineComment


class CommentNodesTestCase(unittest.TestCase):
    """
    Eventually, if a better way to have the lexer some access the
    specific node types for the syntax being processed, this would not
    be necessary.
    """

    def test_block_comment_str_repr(self):
        node = Comments([
            BlockComment(u'/* test1 */'),
            BlockComment(u'/* test2 */'),
        ])
        self.assertEqual(
            "<Comments ?children=[<BlockComment value='/* test1 */'>, "
            "<BlockComment value='/* test2 */'>]>", repr(node)
        )
        self.assertEqual("/* test1 */\n/* test2 */", str(node))

    def test_line_comment_str_repr(self):
        node = Comments([
            LineComment(u'// test1'),
            LineComment(u'// test2'),
        ])
        self.assertEqual("// test1\n// test2", str(node))
