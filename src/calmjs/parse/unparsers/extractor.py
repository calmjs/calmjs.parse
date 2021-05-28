# -*- coding: utf-8 -*-
"""
Description for the extractor unparser
"""

from __future__ import unicode_literals

from ast import literal_eval
from collections import namedtuple
from collections import defaultdict
try:
    from collections.abc import MutableSequence
except ImportError:  # pragma: no cover
    from collections import MutableSequence

from calmjs.parse.asttypes import (
    Assign,
    nodetype,
)
from calmjs.parse.ruletypes import (
    # Space,
    PushScope,
    PopScope,
)
from calmjs.parse.ruletypes import (
    # is_empty,

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
from calmjs.parse.utils import str


ExtractedFragment = namedtuple('ExtractedFragment', ['value', 'node'])


class Assignment(tuple):
    """
    Denote a thing to be assigned.
    """

    def __new__(_cls, key, value):
        return tuple.__new__(_cls, (key, value))

    @property
    def key(self):
        return (
            self[0].value
            if isinstance(self[0], ExtractedFragment) else
            self[0]
        )

    @property
    def value(self):
        return (
            self[1].value
            if isinstance(self[1], ExtractedFragment) else
            self[1]
        )

    def __iter__(self):
        yield self.key
        yield self.value

    def __repr__(self):
        return '(%r, %r)' % (self.key, self.value)


class AssignmentList(MutableSequence):
    """
    A mapping for a list of assignments.
    """

    def __init__(self, *a):
        self.__seq = []
        if len(a) == 1 and isinstance(a[0], AssignmentList):
            self.__seq.extend(a[0])
        else:
            self.extend(a)

    def normalize(self, value):
        if isinstance(value, Assignment):
            return value
        elif isinstance(value, list):
            if len(value) == 2:
                return Assignment(value[0], value[1])
            elif len(value) > 2:
                return Assignment(value[0], value[1:])
        raise ValueError('%r cannot be converted to an Assignment' % (value,))

    def __getitem__(self, index):
        return self.__seq[index]

    def __setitem__(self, index, value):
        self.__seq[index] = self.normalize(value)

    def __delitem__(self, index):
        self.__seq.__delitem__(index)

    def insert(self, index, value):
        self.__seq.insert(index, self.normalize(value))

    # def __iter__(self):
    #     return iter(self.__seq)

    def __len__(self):
        return len(self.__seq)

    def __repr__(self):
        return repr(self.__seq)


# Defining custom ruletype tokens in this module instead of the main
# ruletypes module, simply due to the fact that what is being yielded is
# currently not compatible at all with the default token handler that
# yields stream fragments or layout chunks.
#
# Formalizng this API will be useful, it will be quite a lot of work and
# rather difficult without very strict pre-compile static typing - i.e.
# not possible in Python.

class GroupAs(Token):
    """
    A special token where the provided attr must be a tuple of tokens
    or rules, such that those rules will result in a discrete container
    of all the tokens being yielded, instead of being flattened.

    Provides a common build_items method which may be used to produce
    the list of items.
    """

    def build_items(self, walk, dispatcher, node):
        return (
            item
            # TODO the name argument should really be the name of the
            # type of this node... to help with debugging.
            for attr in dispatcher.optimize_definition('', self.attr)
            for item in attr(walk, dispatcher, node)
        )


class GroupAsAssignment(GroupAs):
    """
    Simply group what was produced by the token as a single assignment.

    There must be two distinct elements, otherwise it will fail.
    """

    def __call__(self, walk, dispatcher, node):
        yield next(dispatcher.token(None, node, AssignmentList(
            list(self.build_items(walk, dispatcher, node))), None))


class GroupAsList(GroupAs):
    """
    Take the processed chunks and remove the context information by
    taking the stored values and return a list.
    """

    def __call__(self, walk, dispatcher, node):
        yield next(dispatcher.token(None, node, [
            v.value for v in self.build_items(walk, dispatcher, node)], None))


class GroupAsMap(GroupAs):
    """
    Take the processed chunks and remove the context information by
    taking the stored values and return a mapping.  Ensure that the
    AssignmentList types are processed for the Assignment entries, and
    extract the unmatched entries into its own list under the
    NotImplemented key.
    """

    def __call__(self, walk, dispatcher, node):
        result = {}
        misc = defaultdict(list)
        for item in self.build_items(walk, dispatcher, node):
            if isinstance(item.value, AssignmentList):
                # in the case of certain in place statement that yielded
                # multiple assignments within the same scope
                result.update(item.value)
            else:
                # if what was produced was not already a list of
                # assignments, chuck it in with the misc list.
                misc[nodetype(item.node)].append(item.value)

        result.update(misc)
        yield next(dispatcher.token(None, node, result, None))


class GroupAsStr(GroupAs):
    """
    Take the processed chunks and extract the value, conver them to text
    and join them together.
    """

    def __call__(self, walk, dispatcher, node):
        joiner = self.value if self.value else ''
        yield next(dispatcher.token(None, node, joiner.join(
            str(s.value) for s in self.build_items(walk, dispatcher, node)
        ), None))


class AttrListAssignment(Attr):
    """
    Specialized attr to produce a ListAssignment.

    The attr argument for the constructor in this case should be a
    2-tuple, first element being the attribute name of the LHS, second
    element being the same for RHS.  Hence LHS becomes the "key", and
    RHS becomes the "value".

    During the production of the yielded Assignmentlist, if the RHS is
    an assignment, the value of the rightmost RHS value will be yielded,
    with the key produced from LHS, along with any other assignment that
    was produced from RHS.
    """

    def __call__(self, walk, dispatcher, node):
        lhs = getattr(node, self.attr[0])
        rhs = getattr(node, self.attr[1])

        def standard_walk():
            # discard all chunk information here?
            # TODO probably should track them to aid with debugging?
            for chunk in walk(dispatcher, lhs, token=self):
                yield chunk.value
            for chunk in walk(dispatcher, rhs, token=self):
                yield chunk.value

        chunks = list(standard_walk())

        if isinstance(rhs, Assign):
            # if RHS is an assign node, yield LHS with the final chunk
            # value produced with the RHS through the walk, then the
            # rest of the chunks produced by the walk.
            yield next(dispatcher.token(None, node, AssignmentList(
                Assignment(chunks[0], chunks[1][-1][1]), *chunks[1]), None))
        else:
            yield next(dispatcher.token(None, node, AssignmentList(
                Assignment(*chunks)), None))


class AttrSink(Attr):
    """
    Used to consume everything declared in the Attr.

    This is used to adapt the Deferrable types such that they get
    processed, but no elements are actually yielded.
    """

    def __call__(self, walk, dispatcher, node):
        list(super(AttrSink, self).__call__(walk, dispatcher, node))
        return
        yield  # pragma: no cover


class LiteralEval(Attr):
    """
    Assume the handler will produce a chunk of type string, and use
    literal_eval to turn it into some underlying value; current intended
    usage is for strings and numbers.
    """

    def __call__(self, walk, dispatcher, node):
        value = self._getattr(dispatcher, node)
        for chunk in walk(dispatcher, value, token=self):
            yield next(dispatcher.token(
                None, node, literal_eval(chunk.value), None))


class Raw(Token):
    """
    Simply yield the raw value as required.
    """

    def __call__(self, walk, dispatcher, node):
        yield next(dispatcher.token(None, node, self.value, None))


class RawBoolean(Attr):
    """
    Simple yield the raw boolean value from the attribute.
    """

    def __call__(self, walk, dispatcher, node):
        value = self._getattr(dispatcher, node)
        if value == 'true':
            yield next(dispatcher.token(None, node, True, None))
        elif value == 'false':
            yield next(dispatcher.token(None, node, False, None))
        # else:
        #     raise ValueError('%r is not a JavaScript boolean value' % value)


class TopLevelAttrs(Attr):
    """
    Denotes a top level attribute generator; should ensure all yielded
    values are all in the form of Assignment, otherwise collate them into
    the "default" NotImplemented key.

    Do note that by yielding naked `Assignment` type, in effect finalizes
    the walker as this type is not handled by other Attr types in this
    module.
    """

    def __call__(self, walk, dispatcher, node):
        # TODO this is getting similar with AsDict
        misc_chunks = defaultdict(list)
        nodes = iter(node)
        for target_node in nodes:
            for chunk in walk(dispatcher, target_node, token=self):
                if isinstance(chunk, ExtractedFragment):
                    if isinstance(chunk.value, AssignmentList):
                        for assignment in chunk.value:
                            yield assignment
                    else:
                        misc_chunks[nodetype(chunk.node)].append(chunk.value)
                else:
                    raise TypeError(
                        "unknown type %r for map grouping" % chunk)

        if misc_chunks:
            for key, value in misc_chunks.items():
                yield Assignment(key, value)


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
    'Block': (
        GroupAsMap((
            JoinAttr(Iter()),
        )),
    ),
    'VarStatement': values,
    'VarDecl': (
        AttrListAssignment(['identifier', 'initializer']),
    ),
    'VarDeclNoIn': (
        # GroupAsList((Attr(Declare('identifier')), Attr('initializer'),),),
        AttrListAssignment(['identifier', 'initializer']),
    ),
    'GroupingOp': (
        Attr('expr'),
    ),
    'Identifier': (
        Attr(Resolve()),
    ),
    'PropIdentifier': value,
    'Assign': (
        AttrListAssignment(['left', 'right']),
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
        GroupAsList((
            Attr('cond'),
            Attr('count'),
        )),
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
    'Continue': (),
    'Break': (),
    'Return': (
        Optional('expr', (
            GroupAsAssignment((
                Text(value='return'),
                Attr(attr='expr'),
            )),
        ),),
    ),
    'With': (
        Attr('expr'),
        Attr('statement'),
    ),
    'Label': (
        GroupAsAssignment((
            Attr(attr='identifier'),
            GroupAsMap((
                Attr(attr='statement'),
            )),
        )),
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
        GroupAsAssignment((
            Attr(Declare('identifier')),
            PushScope,
            GroupAsList((
                Optional('identifier', (ResolveFuncName,)),
                GroupAsList((
                    JoinAttr(Declare('parameters'),),
                )),
                GroupAsMap((
                    JoinAttr('elements'),
                )),
            ),),
            PopScope,
        ),),
    ),
    'FuncExpr': (
        AttrSink(Declare('identifier')),
        PushScope,
        GroupAsList((
            Optional('identifier', (ResolveFuncName,)),
            GroupAsList((
                JoinAttr(Declare('parameters'),),
            )),
            GroupAsMap((
                JoinAttr('elements'),
            )),
        ),),
        PopScope,
    ),
    'Conditional': (
        GroupAsList((
            Attr('predicate'),
            Attr('consequent'),
            Attr('alternative'),
        )),
    ),
    'Regex': value,
    'NewExpr': (
        GroupAsList((Attr('identifier'), Attr('args'),),),
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
        GroupAsList((Attr('identifier'), Attr('args'),),),
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


def token_handler_extractor(
        token, dispatcher, node, subnode, sourcepath_stack=None):
    """
    The token handler that will yield the ExtractedFragment type.
    """

    # Ideally, some kind of simplified bytecode should be generated to
    # instruct how things are assigned by the above rules, such that the
    # origin node can then be encoded as part of the process, but this
    # is a rather huge pain to do (approaching the work of building a
    # proper language interpreter/bytecode compiler, so this shortcut is
    # taken instead.
    yield ExtractedFragment(subnode, node)


class Unparser(BaseUnparser):

    def __init__(
            self,
            definitions=definitions,
            token_handler=token_handler_extractor,
            rules=(),
            layout_handlers=None,
            deferrable_handlers=None,
            prewalk_hooks=()):

        super(Unparser, self).__init__(
            definitions=definitions,
            token_handler=token_handler_extractor,
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
