# -*- coding: utf-8 -*-
import unittest
from collections import namedtuple

from calmjs.parse import es5
from calmjs.parse.asttypes import VarStatement
from calmjs.parse.asttypes import VarDecl
from calmjs.parse.unparsers.prettyprint import State
from calmjs.parse.unparsers.prettyprint import visitor
from calmjs.parse.ruletypes import (
    Attr,
    JoinAttr,
    Text,
    Operator,
    Space,
    Newline,
)

SimpleChunk = namedtuple('SimpleChunk', ['text'])
children_newline = JoinAttr(iter, value=(Newline,))
children_comma = JoinAttr(iter, value=(Text(value=','), Space,))


def setup_handlers(testcase):
    # only provide the bare minimum needed for the tests here.
    testcase.tokens_handled = []
    testcase.layouts_handled = []

    def simple_token_maker(token, state, node, subnode):
        testcase.tokens_handled.append((token, state, node, subnode,))
        yield SimpleChunk(subnode)

    def simple_space(state, node, before, after, prev):
        testcase.layouts_handled.append((state, node, before, after, prev))
        yield SimpleChunk(' ')

    # return token_handler, layout_handlers for State init
    return simple_token_maker, {Space: simple_space}


class PPVisitorTestCase(unittest.TestCase):

    def setUp(self):
        # provide just enough of the everything that is required.
        token_handler, layout_handlers = setup_handlers(self)
        self.state = State(
            definitions={
                'ES5Program': (children_newline, Newline,),
                'VarStatement': (
                    Text(value='var'), Space, children_comma, Text(value=';'),
                ),
                'VarDecl': (
                    Attr('identifier'),
                    Space, Operator(value='='), Space,
                    Attr('initializer'),
                ),
                'Identifier': (Attr('value'),),
                'Number': (Attr('value'),),
            },
            token_handler=token_handler,
            layout_handlers=layout_handlers,
        )

    def test_layouts_buffering(self):
        # The buffered layout rule handler should be invoked with the
        # Node that originally queued the LayoutRuleChunk (rather, the
        # visitor should have done that for the Node).
        original = 'var a = 1;'
        tree = es5(original)
        recreated = ''.join(c.text for c in visitor(
            self.state, tree, self.state[tree]))
        # see that this at least works as expected
        self.assertEqual(original, recreated)
        # ensure that the 3 spaces have been handled as expected
        self.assertEqual(len(self.layouts_handled), 3)
        # the first Space should be derived from VarStatement
        self.assertTrue(isinstance(self.layouts_handled[0][1], VarStatement))
        # last two are in VarDecl
        self.assertTrue(isinstance(self.layouts_handled[1][1], VarDecl))
        self.assertTrue(isinstance(self.layouts_handled[2][1], VarDecl))
