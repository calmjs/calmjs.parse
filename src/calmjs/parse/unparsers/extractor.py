# -*- coding: utf-8 -*-
"""
Description for the extractor unparser
"""

from __future__ import unicode_literals

import operator
from ast import literal_eval
from collections import namedtuple
from collections import defaultdict
from math import floor
from logging import getLogger
try:
    from collections.abc import MutableSequence
except ImportError:  # pragma: no cover
    from collections import MutableSequence

from calmjs.parse.asttypes import (
    Array,
    Assign,
    BinOp,
    Boolean,
    FunctionCall,
    Number,
    Null,
    Object,
    String,
    UnaryExpr,
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
from calmjs.parse.unparsers import walker
from calmjs.parse.utils import str


inf = float('inf')
logger = getLogger(__name__)

# The primary fragment type; token_handler_extractor yields these
ExtractedFragment = namedtuple('ExtractedFragment', [
    'value',
    'node',
    'folded_type',
])
# The secondary fragment type; may be used as value so that the
# token_handler_extractor be able to produce a folded_type
FoldedFragment = namedtuple('FoldedFragment', [
    'value',
    'folded_type',
])


# See ECMA-262 5.1 Edition, Section 9
# Note that this parser does not provide an undefined token or global
# binding, it's currently not handled.

def value_to_str(value):
    """
    Since the design eagerly convert and discard because it was felt
    that tracking everything all at once being too cumbersome, there
    will be situations where this conversion from Python values back
    to JavaScript equivalent string expression...

    This is currently used for converting converted values enclosed in
    Array back to the JavaScript string converted types; not to be used
    in subsequent methods due to subtle differences with the conversion
    of null.
    """

    if value is None:  # null
        return ''
    elif value is True:  # true
        return 'true'
    elif value is False:  # false
        return 'false'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return value
    elif isinstance(value, list):
        return ','.join([value_to_str(v) for v in value])
    elif isinstance(value, dict):
        return '[object Object]'
    raise TypeError(
        '%r cannot be converted to a value in the base ECMAScript '
        'language type' % value)


def to_primitive(fragment, hint):
    # The hint argument is the PreferredType
    if (issubclass(fragment.folded_type, Array) or
            issubclass(fragment.folded_type, Object)):
        value = value_to_str(fragment.value)
        if issubclass(hint, Number):
            return FoldedFragment(
                to_number(FoldedFragment(value, String)), Number)
        # everything else?
        return FoldedFragment(value, String)
    # no conversion for other types.
    return fragment


def to_boolean(fragment):
    if issubclass(fragment.folded_type, Array):
        return True
    elif issubclass(fragment.folded_type, Boolean):
        return fragment.value
    elif issubclass(fragment.folded_type, Number):
        return fragment.value not in (0, 'NaN')
    elif issubclass(fragment.folded_type, String):
        return bool(fragment.value)
    elif issubclass(fragment.folded_type, Object):
        return True
    return False


def to_number(fragment):
    def from_str(value):
        # probably not exactly spec conformant, but close enough.
        maybe_hex = value.strip()
        if maybe_hex.startswith('0x'):
            cleaned = maybe_hex
        else:
            cleaned = maybe_hex.lstrip('0')
        if cleaned == '':
            return 0
        try:
            number = literal_eval(cleaned)
        except (ValueError, SyntaxError):
            return 'NaN'
        if not isinstance(number, (int, float)):
            return 'NaN'
        return number

    if issubclass(fragment.folded_type, Array):
        return to_primitive(fragment, Number).value
    elif issubclass(fragment.folded_type, Boolean):
        return int(fragment.value)
    elif issubclass(fragment.folded_type, Number):
        return fragment.value
    elif issubclass(fragment.folded_type, Null):
        return 0
    elif issubclass(fragment.folded_type, String):
        return from_str(fragment.value)
    elif issubclass(fragment.folded_type, Object):
        return to_primitive(fragment, Number).value
    return 'NaN'


def to_integer(fragment):
    value = to_number(fragment)
    if value == 'NaN':
        return 0
    if value in (0, inf):
        return value
    return (1 if abs(value) == value else -1) * int(floor(abs(value)))


def to_uint32(fragment):
    value = to_integer(fragment)
    if value in ('NaN', 0, inf):
        return value
    posint = (1 if abs(value) == value else -1) * int(floor(abs(value)))
    return posint % 2 ** 32


def to_int32(fragment):
    int32bit = to_uint32(fragment)
    if int32bit >= 2 ** 31:
        return int32bit - 2 ** 32
    else:
        return int32bit


def to_string(fragment):
    # can't quite use value_to_str because that's for values enclosed in
    # another object.
    if issubclass(fragment.folded_type, Array):
        return to_string(to_primitive(fragment, String))
    elif issubclass(fragment.folded_type, Boolean):
        return 'true' if fragment.value else 'false'
    elif issubclass(fragment.folded_type, Number):
        return str(fragment.value)
    elif issubclass(fragment.folded_type, Null):
        return 'null'
    elif issubclass(fragment.folded_type, String):
        return fragment.value
    elif issubclass(fragment.folded_type, Object):
        return to_string(to_primitive(fragment, String))

    # For other unsupported values; if the fragment value is a string
    # type, assume it is some kind of resolvable identifier that may be
    # used as a format placeholder token.
    elif isinstance(fragment.value, str):
        return '{%s}' % fragment.value
    # Function Calls have been destructured, but given that it is
    # impractical to reapply as is, just replace with an anonymous
    # field.
    elif issubclass(fragment.folded_type, FunctionCall):
        return '{}'
    # Otherwise, return an empty string.
    return ''


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

    def __eq__(self, other):
        return self.__seq == other


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


class OpDisambiguate(Token):
    """
    A special token that deals with nodes with an `op` attribute, such
    that it will be used to determine the handling to use through the
    mapping specified with the value provided for the construction of
    this token.

    A default token should be specified with the key `NotImplemented`.
    """

    def __call__(self, walk, dispatcher, node):
        definition = dispatcher.optimize_definition('', self.value.get(
            node.op, self.value.get(NotImplemented, ())))
        for rule in definition:
            for chunk in rule(walk, dispatcher, node):
                yield chunk


class GroupAsBinOp(GroupAs):
    """
    The generic binop
    """

    def _next_one(self, walk, dispatcher, node):
        gen = walk(dispatcher, node, definition=None)
        result = next(gen)
        try:
            fail = next(gen)
        except StopIteration:
            return result
        else:
            # TODO exception type
            raise ValueError(
                "Ruletype token %r unable to process output produced by the "
                "definition used on <%s @%s:%s ...>, as it yielded more than "
                "one fragment (first two fragments are %r and %r)" % (
                    type(self).__name__,
                    # manually construct a zero depth with line number
                    type(node).__name__,
                    '?' if node.lineno is None else node.lineno,
                    '?' if node.colno is None else node.colno,
                    result,
                    fail,
                )
            )

    def __call__(self, walk, dispatcher, node):
        if not isinstance(node, BinOp):
            raise TypeError(
                "Ruletype token %r expects a 'BinOp', got %r" % (
                    type(self).__name__, type(node).__name__))

        lhs = self._next_one(walk, dispatcher, node.left)
        rhs = self._next_one(walk, dispatcher, node.right)
        yield next(dispatcher.token(None, node, self.binop(lhs, rhs), None))

    def binop(self, lhs, rhs):
        """
        Default implementation is the most common form.
        """

        # assumes to be ExtractedFragments
        lhs_value = to_number(lhs)
        rhs_value = to_number(rhs)
        if lhs_value == 'NaN' or rhs_value == 'NaN':
            return FoldedFragment('NaN', Number)
        else:
            try:
                return FoldedFragment(self.op(lhs_value, rhs_value), Number)
            except ArithmeticError:
                return FoldedFragment('NaN', Number)

    def op(self, lhs, rhs):
        raise NotImplementedError


class GroupAsBinOpPlus(GroupAsBinOp):
    """
    For BinOp with op = '+'
    """

    def binop(self, lhs, rhs):
        """
        The plus operator is a bit different from the rest.
        """

        if issubclass(lhs.folded_type, Number) and issubclass(
                rhs.folded_type, Number):
            return FoldedFragment(lhs.value + rhs.value, Number)
        else:
            return FoldedFragment(to_string(lhs) + to_string(rhs), String)


class GroupAsBinOpMinus(GroupAsBinOp):
    """
    For BinOp with op = '-'
    """

    op = operator.sub


class GroupAsBinOpMult(GroupAsBinOp):
    """
    For BinOp with op = '*'
    """

    op = operator.mul


class GroupAsBinOpDiv(GroupAsBinOp):
    """
    For BinOp with op = '*'
    """

    op = operator.truediv


class GroupAsBinOpMod(GroupAsBinOp):
    """
    For BinOp with op = '*'
    """

    op = operator.mod


class GroupAsBinOpLeftShift(GroupAsBinOp):
    """
    For BinOp with op = '<<'
    """

    def binop(self, lhs, rhs):
        return to_int32(
            FoldedFragment(to_int32(lhs) << (to_uint32(rhs) & 0x1f), Number))


class GroupAsBinOpRightShift(GroupAsBinOp):
    """
    For BinOp with op = '>>'
    """

    def binop(self, lhs, rhs):
        return to_int32(
            FoldedFragment(to_int32(lhs) >> (to_uint32(rhs) & 0x1f), Number))


class GroupAsBinOpUnsignedRightShift(GroupAsBinOp):
    """
    For BinOp with op = '>>>'
    """

    def binop(self, lhs, rhs):
        return to_uint32(
            FoldedFragment(to_uint32(lhs) >> (to_uint32(rhs) & 0x1f), Number))


class GroupAsBinOpBitwise(GroupAsBinOp):
    """
    Generic binop bitwise
    """

    def binop(self, lhs, rhs):
        """
        The plus operator is a bit different from the rest.
        """

        return FoldedFragment(self.op(to_int32(lhs), to_int32(rhs)), Number)

    def op(self, lhs, rhs):
        raise NotImplementedError


class GroupAsBinOpBitwiseAnd(GroupAsBinOpBitwise):
    """
    For BinOp with op = '&'
    """

    op = operator.and_


class GroupAsBinOpBitwiseXor(GroupAsBinOpBitwise):
    """
    For BinOp with op = '^'
    """

    op = operator.xor


class GroupAsBinOpBitwiseOr(GroupAsBinOpBitwise):
    """
    For BinOp with op = '|'
    """

    op = operator.or_


class GroupAsBinOpLogicalAnd(GroupAsBinOp):

    def binop(self, lhs, rhs):
        if not to_boolean(lhs):
            return FoldedFragment(lhs.value, type(lhs.node))
        else:
            return FoldedFragment(rhs.value, type(rhs.node))


class GroupAsBinOpLogicalOr(GroupAsBinOp):

    def binop(self, lhs, rhs):
        if to_boolean(lhs):
            return FoldedFragment(lhs.value, type(lhs.node))
        else:
            return FoldedFragment(rhs.value, type(rhs.node))


class UnaryOptionalSpace(Token):

    def __call__(self, walk, dispatcher, node):
        value = '' if node.op in {'++', '--', '!', '~', '+', '-'} else ' '
        yield next(dispatcher.token(None, node, value, None))


class GroupAsUnaryExpr(Attr):

    def __call__(self, walk, dispatcher, node):
        if not isinstance(node, UnaryExpr):
            raise TypeError(
                "Ruletype token %r expects a 'UnaryExpr', got %r" % (
                    type(self).__name__, type(node).__name__))

        value = next(walk(dispatcher, node.value, definition=None))
        yield next(dispatcher.token(None, node, self.unaryop(value), None))

    def unaryop(self, value):
        # assumes to be ExtractedFragments
        value = to_number(value)
        if value == 'NaN':
            return FoldedFragment('NaN', Number)
        else:
            return FoldedFragment(self.op(value), Number)

    def op(self, value):
        raise NotImplementedError


class GroupAsUnaryExprPlus(GroupAsUnaryExpr):
    """
    For UnaryExpr with op = '+'
    """

    def op(self, value):
        return value


class GroupAsUnaryExprMinus(GroupAsUnaryExpr):
    """
    For UnaryExpr with op = '-'
    """

    def op(self, value):
        return - value


class GroupAsUnaryExprBitwiseNot(GroupAsUnaryExpr):
    """
    For UnaryExpr with op = '~'
    """

    def unaryop(self, value):
        return FoldedFragment(~ to_int32(value), Number)


class GroupAsUnaryExprLogicalNot(GroupAsUnaryExpr):
    """
    For UnaryExpr with op = '!'
    """

    def unaryop(self, value):
        return FoldedFragment(not to_boolean(value), Boolean)


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


class OpString(Token):
    """
    Special case for the BinOp/UnaryExpr, to ensure that the raw value
    that was parsed into the ast node is returned instead of being
    treated, such that the original expression have their quotes
    preserved.
    """

    def __call__(self, walk, dispatcher, node):
        value = getattr(node, self.attr)
        if isinstance(value, String):
            yield next(dispatcher.token(None, node, value.value, None))
        else:
            for chunk in walk(dispatcher, value, token=self):
                yield chunk


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
        else:
            raise ValueError('%r is not a JavaScript boolean value' % value)


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
                    # ideally, walk.throw() be called instead as the
                    # exception would propagate to the real ruletype
                    # responsible, but would also completely kill this
                    # generator; so instead just invoke the dispatcher
                    # error_handler.
                    dispatcher.error_handler(
                        TypeError(
                            "generated value %r is not an instance of "
                            "ExtractedFragment, thus it cannot be yielded by "
                            "instances of %r; check that all ruletypes "
                            "specified for target node type %r such that "
                            "the values generate by them are done through "
                            "walk or dispatcher.token, or yield instances of "
                            "ExtractedFragment." % (
                                chunk,
                                type(self),
                                target_node,
                            )
                        ),
                        rule=self,
                        node=target_node,
                    )

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
        GroupAsList((
            Attr('predicate'),
            GroupAsMap((
                Attr('consequent'),
            ),),
            GroupAsMap((
                Attr('alternative'),
            ),),
        ),),
    ),
    'Boolean': (
        RawBoolean('value'),
    ),
    'For': (
        Attr('init'),
        GroupAsList((
            Attr('cond'),
            Attr('count'),
            GroupAsMap((
                Attr('statement'),
            ),),
        )),
    ),
    'ForIn': (
        GroupAsList((
            Attr('item'),
            Attr('iterable'),
            GroupAsMap((
                Attr('statement'),
            ),),
        ),),
    ),
    'BinOp': (GroupAsStr((
        OpString('left'), Text(value=' '),
        Operator(attr='op'),
        Text(value=' '), OpString('right'),
    ),),),
    'UnaryExpr': (
        # the default grouping required to ensure positive/negative
        # numbers return as expected.
        OpDisambiguate(
            value={
                NotImplemented: (GroupAsStr(
                    (Attr('op'), UnaryOptionalSpace(), OpString('value')),
                    value='',
                ),),
                '+': (GroupAsUnaryExprPlus(),),
                '-': (GroupAsUnaryExprMinus(),),
            }
        ),
    ),
    'PostfixExpr': (
        Operator(attr='value'),
    ),
    'ExprStatement': (
        Attr('expr'),
    ),
    'DoWhile': (
        GroupAsList((
            GroupAsMap((Attr('statement'),),),
            Attr('predicate'),
        ),),
    ),
    'While': (
        GroupAsList((
            Attr('predicate'),
            GroupAsMap((Attr('statement'),),),
        ),),
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
        GroupAsList((
            Attr('expr'),
            GroupAsMap((Attr('statement'),),),
        ),),
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
        GroupAsList((
            Attr('expr'),
            Attr('case_block'),
        ),),
    ),
    'CaseBlock': (
        GroupAsMap((
            JoinAttr(Iter()),
        )),
    ),
    'Case': (
        GroupAsList((
            Attr('expr'),
            GroupAsMap((
                JoinAttr('elements'),
            ),),
        ),),
    ),
    'Default': (
        GroupAsList((
            GroupAsMap((
                JoinAttr('elements'),
            ),),
        ),),
    ),
    'Throw': (
        Attr('expr'),
    ),
    'Debugger': (),
    'Try': (
        GroupAsList((
            Attr('statements'),
            Attr('catch'),
            Attr('fin'),
        ),),
    ),
    'Catch': (
        GroupAsMap((
            GroupAsList((
                Attr('identifier'),
                Attr('elements'),
            ),),
        ),),
    ),
    'Finally': (
        GroupAsMap((
            GroupAsList((
                Attr('elements'),
            ),),
        ),),
    ),
    'FuncDecl': (
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
    if isinstance(subnode, FoldedFragment):
        value, folded_type = subnode
    else:
        value, folded_type = subnode, nodetype(node)
    yield ExtractedFragment(value, node, folded_type)


class Dispatcher(walker.Dispatcher):

    def error_handler(self, exception, rule=None, node=None):
        logger.error(
            "failed to process node %r with rule %r to an extracted value; "
            "cause: %s: %s",
            node, type(rule).__name__, type(exception).__name__, exception
        )
        return next(self.token(rule, node, '', []))


class Unparser(BaseUnparser):

    def __init__(
            self,
            definitions=definitions,
            token_handler=token_handler_extractor,
            rules=(),
            layout_handlers=None,
            deferrable_handlers=None,
            prewalk_hooks=(),
            dispatcher_cls=walker.Dispatcher):

        super(Unparser, self).__init__(
            definitions=definitions,
            token_handler=token_handler_extractor,
            rules=rules,
            layout_handlers=layout_handlers,
            deferrable_handlers=deferrable_handlers,
            prewalk_hooks=prewalk_hooks,
            dispatcher_cls=dispatcher_cls,
        )


def extractor(fold_ops=False, ignore_errors=False):
    """
    A helper to construct an instance of the extractor Unparser

    arguments

    fold_ops
        Apply an update to a clone of the definitions defined at the
        root of this module such that the definition fo BinOp will be
        modified with a default set of GroupAsBinOp tokens that will
        process the operand with the associated operator token.

        This would result in constants (such as Numbers and Strings)
        being evaluated with the associated operator, yielding an
        evaluated expression or concatenated strings.  For other
        identifiers and types encountered, they are simply replaced with
        a string format replacement fields and are simply treated as if
        they are strings (i.e. result will be a concatenation).

        This flag has significant limitations and the resulting values
        of limited value, given that no JavaScript engine or real
        execution of the code is done.  It WILL produce wild and
        unexpected results.  Use with caution.

        Default: false (operators will simply be concatenated together
        with the operands as a string to produce values).

    ignore_errors
        Attempt to continue through errors triggered through processing
        of the input ast through the unparser.

        Default: false (exceptions will be thrown on error).
    """

    dispatcher_cls = Dispatcher if ignore_errors else walker.Dispatcher
    new_definitions = {}
    new_definitions.update(definitions)
    if fold_ops:
        new_definitions.update({
            'BinOp': (
                OpDisambiguate(
                    value={
                        NotImplemented: (GroupAsStr((
                            Attr('left'), Text(value=' '),
                            Operator(attr='op'),
                            Text(value=' '), Attr('right'),
                        ),),),
                        '+': (GroupAsBinOpPlus(),),
                        '-': (GroupAsBinOpMinus(),),
                        '*': (GroupAsBinOpMult(),),
                        '/': (GroupAsBinOpDiv(),),
                        '%': (GroupAsBinOpMod(),),
                        '<<': (GroupAsBinOpLeftShift(),),
                        '>>': (GroupAsBinOpRightShift(),),
                        '>>>': (GroupAsBinOpUnsignedRightShift(),),
                        '&': (GroupAsBinOpBitwiseAnd(),),
                        '^': (GroupAsBinOpBitwiseXor(),),
                        '|': (GroupAsBinOpBitwiseOr(),),
                        '&&': (GroupAsBinOpLogicalAnd(),),
                        '||': (GroupAsBinOpLogicalOr(),),
                    }
                ),
            ),
            'UnaryExpr': (
                OpDisambiguate(
                    value={
                        NotImplemented: (GroupAsStr(
                            (Attr('op'), UnaryOptionalSpace(),
                                OpString('value')),
                            value='',
                        ),),
                        '+': (GroupAsUnaryExprPlus(),),
                        '-': (GroupAsUnaryExprMinus(),),
                        '~': (GroupAsUnaryExprBitwiseNot(),),
                        '!': (GroupAsUnaryExprLogicalNot(),),
                    }
                ),
            ),
        })

    return Unparser(definitions=new_definitions, dispatcher_cls=dispatcher_cls)


def ast_to_dict(ast, fold_ops=False, ignore_errors=False):
    """
    Simple dictionary building function - return a dictionary for the
    source abstract syntax tree for the parsed program.

    arguments

    ast
        The AST to convert to a dictionary.

    fold_ops
        Apply an update to a clone of the definitions defined at the
        root of this module such that the definition fo BinOp will be
        modified with a default set of GroupAsBinOp tokens that will
        process the operand with the associated operator token.

        This would result in constants (such as Numbers and Strings)
        being evaluated with the associated operator, yielding an
        evaluated expression or concatenated strings.  For other
        identifiers and types encountered, they are simply replaced with
        a string format replacement fields and are simply treated as if
        they are strings (i.e. result will be a concatenation).

        This flag has significant limitations and the resulting values
        of limited value, given that no JavaScript engine or real
        execution of the code is done.  It WILL produce wild and
        unexpected results.  Use with caution.

        Default: false (operators will simply be concatenated together
        with the operands as a string to produce values).

    ignore_errors
        Attempt to continue through errors triggered through processing
        of the input ast through the unparser.

        Default: false (exceptions will be thrown on error).
    """

    return dict(extractor(fold_ops=fold_ops, ignore_errors=ignore_errors)(ast))
