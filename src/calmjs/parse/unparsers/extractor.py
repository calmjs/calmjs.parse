# -*- coding: utf-8 -*-
"""
Description for the extractor unparser
"""

from __future__ import unicode_literals

from ast import literal_eval

from calmjs.parse.asttypes import (
    Assign,
)
from calmjs.parse.ruletypes import (
    # Space,
    PushScope,
    PopScope,
)
from calmjs.parse.ruletypes import (
    is_empty,

    Attr,
    Token,
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


class AssignmentChunk(list):
    """
    Marker list type for an assignment chunk.
    """


# Defining custom ruletype tokens in this module instead of the main
# ruletypes module, simply due to the fact that what is being yielded is
# currently not compatible at all with the text chunks, and while
# formalizng this API will be useful, it is quite a lot of work and
# rather difficult without very strict pre-compile static typing - i.e.
# not possible in Python.

class GroupAs(Token):
    """
    A special token where the provided attr must be a tuple of tokens
    or rules, such that those rules will result in a discrete container
    of all the tokens being yielded, instead of being flattened.
    """

    def __call__(self, walk, dispatcher, node):
        yield [
            item
            # TODO the name argument should really be the name of the
            # type of this node... to help with debugging.
            for attr in dispatcher.optimize_definition('', self.attr)
            for item in attr(walk, dispatcher, node)
        ]


class GroupAsMap(GroupAs):
    """
    Leverage the parent GroupAs.__call__ to produce a list of maps and
    assume that the produced output will be list of 2-tuples, which is
    then passed directly to the dict constructor.
    """

    def __call__(self, walk, dispatcher, node):
        result = {}
        for item in next(
                super(GroupAsMap, self).__call__(walk, dispatcher, node)):
            if len(item) != 2:
                continue
            key, value = item
            try:
                # TODO need to figure out how sometimes optional
                # identifiers for the map might not percolate to the
                # generator...
                hash(key)
            except TypeError:
                continue
            result[key] = value
        yield result


class GroupAsStr(GroupAs):
    """
    Leverage the parent GroupAs.__call__ to produce a str, assuming
    that the produced output will be a list of str, which is then passed
    to the string joiner, the value.
    """

    def __call__(self, walk, dispatcher, node):
        joiner = self.value if self.value else ''
        yield joiner.join(
            str(s) for s in
            next(super(GroupAsStr, self).__call__(walk, dispatcher, node))
        )


class GroupAssign(GroupAs):
    """
    Special grouping for assignment.  If the RHS is an assignment, the
    RHS of the value will be yielded.

    The attr in this case should be a 2-tuple, first element being the
    attribute name of the LHS, second element being the same for RHS.
    """

    def __call__(self, walk, dispatcher, node):
        lhs = getattr(node, self.attr[0])
        rhs = getattr(node, self.attr[1])

        def standard_walk():
            for chunk in walk(dispatcher, lhs, token=self):
                yield chunk
            for chunk in walk(dispatcher, rhs, token=self):
                yield chunk

        chunks = AssignmentChunk(standard_walk())

        if isinstance(rhs, Assign):
            # if RHS is an assign node, yield LHS with the final chunk
            # value produced with the RHS through the walk, then the
            # rest of the chunks produced by the walk.
            yield AssignmentChunk([chunks[0], chunks[-1][1]])
            for chunk in chunks[1:]:
                yield chunk
        else:
            yield chunks


GroupAsList = GroupAsCall = GroupAs


class LiteralEval(Attr):
    """
    Assume the handler will produce a chunk of type string, and use
    literal_eval to turn it into some underlying value; current intended
    usage is for strings and numbers.
    """

    def __call__(self, walk, dispatcher, node):
        value = self._getattr(dispatcher, node)
        if is_empty(value):
            return
        for chunk in walk(dispatcher, value, token=self):
            yield literal_eval(chunk)


class Raw(Token):
    """
    Simply yield the raw value as required.
    """

    def __call__(self, walk, dispatcher, node):
        yield self.value


class RawBoolean(Attr):
    """
    Simple yield the raw boolean value from the attribute.
    """

    def __call__(self, walk, dispatcher, node):
        value = self._getattr(dispatcher, node)
        if value == 'true':
            yield True
        elif value == 'false':
            yield False
        else:
            raise ValueError('%r is not a JavaScript boolean value' % value)


class TopLevelAttrs(Attr):
    """
    Denotes a top level attribute generator; should ensure all yielded
    values are all in the form of 2-tuple, otherwise collate them into
    the "default" NotImplemented key.
    """

    def __call__(self, walk, dispatcher, node):
        misc_chunks = []
        nodes = iter(node)
        for target_node in nodes:
            for chunk in walk(dispatcher, target_node, token=self):
                if isinstance(chunk, AssignmentChunk):
                    yield chunk
                else:
                    misc_chunks.append(chunk)

        if misc_chunks:
            yield AssignmentChunk([NotImplemented, misc_chunks])


value = (
    Attr('value'),
)
values = (
    JoinAttr(Iter()),
)
top_level_values = (
    TopLevelAttrs(),
)

# definitions of all the rules for all the types for an ES5 program.
definitions = {
    'ES5Program': top_level_values,
    'Block': top_level_values,
    'VarStatement': values,
    'VarDecl': (
        GroupAssign(['identifier', 'initializer']),
    ),
    'VarDeclNoIn': (
        GroupAsList((Attr(Declare('identifier')), Attr('initializer'),),),
    ),
    'GroupingOp': (
        Attr('expr'),
    ),
    'Identifier': (
        Attr(Resolve()),
    ),
    'PropIdentifier': value,
    'Assign': (
        GroupAssign(['left', 'right']),
    ),
    'GetPropAssign': (
        GroupAsList((
            Attr('prop_name'),
            PushScope,
            GroupAsMap((
                JoinAttr(attr='elements'),
            )),
            PopScope,
        ),),
    ),
    'SetPropAssign': (
        GroupAsList((
            Attr('prop_name'),
            PushScope,
            GroupAsMap((
                JoinAttr(attr='elements'),
            )),
            PopScope,
        ),),
    ),
    'Number': (
        LiteralEval('value'),
    ),
    'Comma': (
        Attr('left'), Attr('right'),
    ),
    'EmptyStatement': (),
    'If': (
        Attr('predicate'),
        Attr('consequent'),
        Optional('alternative', (Attr('alternative'),),),
    ),
    'Boolean': (
        RawBoolean('value'),
    ),
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
        # Note that this can be replaced with an statement evaluator to
        # calculate/derived/evaluate the inputs into a result.
        GroupAsStr((
            Attr('left'), Text(value=' '),
            Operator(attr='op'),
            Text(value=' '), Attr('right'),
        ),),
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
        Raw(value=None),
    ),
    'String': (
        LiteralEval(Literal()),
    ),
    'Continue': (
        Optional('identifier', (Attr(attr='identifier'),),),
    ),
    'Break': (
        Optional('identifier', (Attr(attr='identifier'),),),
    ),
    'Return': (
        GroupAsList((
            Text(value='return'),
            Optional('expr', (Attr(attr='expr'),),),
        )),
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
        GroupAsMap((
            Attr(Declare('identifier')),
            GroupAsList((
                PushScope,
                Optional('identifier', (ResolveFuncName,)),
                JoinAttr(Declare('parameters'),),
                JoinAttr('elements'),
                PopScope,
            ),),
        ),),
    ),
    'FuncExpr': (
        Attr(Declare('identifier')),
        PushScope,
        GroupAsList((
            Optional('identifier', (ResolveFuncName,)),
            JoinAttr(Declare('parameters'),),
            JoinAttr('elements'),
        ),),
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
        # The current way may simply result in a binding that has a dot,
        # this may be desirable now, however an alternative manner is to
        # implement registration and update of the value within the
        # scope...
        GroupAsStr(
            (Attr('node'), Text(value='.'), Attr('identifier'),),
            value='',
        ),
    ),
    'BracketAccessor': (
        # Likewise similar as above
        GroupAsStr(
            (Attr('node'), Text(value='['), Attr('expr'), Text(value=']'),),
            value='',
        ),
    ),
    'FunctionCall': (
        GroupAsCall((Attr('identifier'), Attr('args'),),),
    ),
    'Arguments': (
        GroupAsList((JoinAttr('items',),),),
    ),
    'Object': (
        GroupAsMap((JoinAttr('properties'),)),
    ),
    'Array': (
        GroupAsList((JoinAttr('items'),),),
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

    # Ideally, some kind of simplified bytecode should be generated to
    # instruct how things are assigned by the above rules, such that the
    # origin node can then be encoded as part of the process, but this
    # is a rather huge pain to do so this is ignored for now...
    yield subnode


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
        yield chunk
