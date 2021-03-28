# -*- coding: utf-8 -*-
"""
Description for the extractor unparser
"""

from __future__ import unicode_literals

from calmjs.parse.ruletypes import (
    StreamFragment,
)
from calmjs.parse.ruletypes import (
    PushScope,
    PopScope,
)
from calmjs.parse.ruletypes import (
    Attr,
    Iter,
    Text,
    Optional,
    JoinAttr,
    Operator,
)
from calmjs.parse.ruletypes import (
    Literal,
    Declare,
    Resolve,
    ResolveFuncName,
)
from calmjs.parse.unparsers.base import BaseUnparser

value = (
    Attr('value'),
)
values = (
    JoinAttr(Iter()),
)

# definitions of all the rules for all the types for an ES5 program.
definitions = {
    'ES5Program': values,
    'Block': values,
    'VarStatement': values,
    'VarDecl': (
        Attr(Declare('identifier')), Attr('initializer'),
    ),
    'VarDeclNoIn': (
        Attr(Declare('identifier')), Attr('initializer'),
    ),
    'GroupingOp': (
        Attr('expr'),
    ),
    'Identifier': (
        Attr(Resolve()),
    ),
    'PropIdentifier': value,
    'Assign': (
        Attr('left'), Attr('right'),
    ),
    'GetPropAssign': (
        Attr('prop_name'),
        PushScope,
        JoinAttr(attr='elements'),
        PopScope,
    ),
    'SetPropAssign': (
        Attr('prop_name'),
        PushScope,
        JoinAttr(attr='elements'),
        PopScope,
    ),
    'Number': value,  # FIXME
    'Comma': (
        Attr('left'), Attr('right'),
    ),
    'EmptyStatement': (),
    'If': (
        Attr('predicate'),
        Attr('consequent'),
        Optional('alternative', (Attr('alternative'),),),
    ),
    'Boolean': value,  # FIXME
    'For': (
        Attr('init'),
        Attr('cond'),
        Attr('count'),
        Attr('statement'),
    ),
    'ForIn': (
        Attr('item'),
        Attr('iterable'),
        Attr('statement'),
    ),
    'BinOp': (
        Attr('left'), Attr('right'),
    ),
    'UnaryExpr': (
        Attr('value'),
    ),
    'PostfixExpr': (
        Operator(attr='value'),
    ),
    'ExprStatement': (
        Attr('expr'),
    ),
    'DoWhile': (
        Attr('statement'),
        Attr('predicate'),
    ),
    'While': (
        Attr('predicate'),
        Attr('statement'),
    ),
    'Null': (
        Text(value='null'),  # FIXME Null()
    ),
    'String': (
        Attr(Literal()),
    ),
    'Continue': (
        Optional('identifier', (Attr(attr='identifier'),),),
    ),
    'Break': (
        Optional('identifier', (Attr(attr='identifier'),),),
    ),
    'Return': (
        Text(value='return'),
        Optional('expr', (Attr(attr='expr'),),),
    ),
    'With': (
        Attr('expr'),
        Attr('statement'),
    ),
    'Label': (
        Attr('identifier'), Attr('statement'),
    ),
    'Switch': (
        Attr('expr'),
        Attr('case_block'),
    ),
    'CaseBlock': values,
    'Case': (
        Attr('expr'),
        JoinAttr('elements'),
    ),
    'Default': (
        JoinAttr('elements',),
    ),
    'Throw': (
        Attr('expr'),
    ),
    'Debugger': (),
    'Try': (
        Attr('statements'),
        Optional('catch', (Attr('catch'),),),
        Optional('fin', (Attr('fin'),),),
    ),
    'Catch': (
        Attr('identifier'),
        Attr('elements'),
    ),
    'Finally': (
        Attr('elements'),
    ),
    'FuncDecl': (
        # TODO DeclareAsFunc?
        Attr(Declare('identifier')),
        PushScope,
        Optional('identifier', (ResolveFuncName,)),
        JoinAttr(Declare('parameters'),),
        JoinAttr('elements'),
        PopScope,
    ),
    'FuncExpr': (
        Attr(Declare('identifier')),
        PushScope,
        Optional('identifier', (ResolveFuncName,)),
        JoinAttr(Declare('parameters'),),
        JoinAttr('elements'),
        PopScope,
    ),
    'Conditional': (
        Attr('predicate'),
        Attr('consequent'),
        Attr('alternative'),
    ),
    'Regex': value,
    'NewExpr': (
        Attr('identifier'), Attr('args'),
    ),
    'DotAccessor': (
        # TODO
        Attr('node'), Text(value='.'), Attr('identifier'),
    ),
    'BracketAccessor': (
        # TODO token for dealing with reassignment??
        Attr('node'), Attr('expr'),
    ),
    'FunctionCall': (
        Attr('identifier'), Attr('args'),
    ),
    'Arguments': (
        JoinAttr('items',),
    ),
    'Object': (
        Optional('properties', (JoinAttr('properties'),)),
    ),
    'Array': (
        JoinAttr('items'),
    ),
    'Elision': (),
    'This': (
        Text(value='this'),
    ),
    'Comments': (),
    'LineComment': (),
    'BlockComment': (),
}


def token_handler_basic(
        token, dispatcher, node, subnode, sourcepath_stack=None):
    """
    The basic token handler that will return the value and nothing else.
    """

    yield StreamFragment(subnode, None, None, None, None)


class Unparser(BaseUnparser):

    def __init__(
            self,
            definitions=definitions,
            token_handler=token_handler_basic,
            rules=(),
            layout_handlers=None,
            deferrable_handlers=None,
            prewalk_hooks=()):

        super(Unparser, self).__init__(
            definitions=definitions,
            token_handler=token_handler_basic,
            rules=rules,
            layout_handlers=layout_handlers,
            deferrable_handlers=deferrable_handlers,
            prewalk_hooks=prewalk_hooks,
        )


def extractor():
    """
    Construct the default extractor unparser
    """

    return Unparser()


def build_dict(ast):
    """
    Simple dictionary building function - return a dictionary for the
    source tree for the program.

    arguments

    ast
        The AST to pretty print
    """

    for chunk in Unparser()(ast):
        yield chunk.text
