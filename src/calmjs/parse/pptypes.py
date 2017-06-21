# -*- coding: utf-8 -*-
"""
Types for pretty printing.
"""

from calmjs.parse.asttypes import Node


class Rule(object):
    """
    The base type.
    """


class Layout(Rule):
    """
    Layout rules are simply for building markers that either return some
    extraneous fragments or set some flags on the state object for
    further usage, so that the pretty printing will look pretty.

    The subclasses will be used as types for the handler lookup (i.e.
    they will serve as keys); for the subclasses to be used as par of
    the definition for the structure of a given asttype, it must be
    instantiated.
    """


class Token(Rule):
    """
    Token rules are callable rules that will directly take part in
    ochestrating the rendering of the given input node, along with the
    visitor function and the state object that tracks the currently
    executing prettyprint iteration.

    Like the Layout type, Token types must also be instantiated before
    they can be used.
    """

    def __init__(self, attr=None, value=None, pos=0):
        self.attr = attr
        self.value = value
        self.pos = pos

    def resolve(self, visitor, state, node, value):
        if isinstance(value, Node):
            return visitor(state, value, state[value])
        else:
            return state(self)(self, state, node, value)

    def __call__(self, visitor, state, node):
        """
        Arguments

        visitor
            the visitor function
        state
            a PrettyPrintState instance.
        node
            a Node instance.
        """

        raise NotImplementedError


class Space(Layout):
    """
    Represents a space.
    """


class OptionalSpace(Layout):
    """
    Represents optional space character.
    """


class Newline(Layout):
    """
    Represents a newline character.
    """


class OptionalNewline(Layout):
    """
    Represents an optional newline character.
    """


class Indent(Layout):
    """
    Represents an increment to the indentation level.
    """


class Dedent(Layout):
    """
    Represents an decrement to the indentation level.
    """


class Attr(Token):
    """
    Return the value as specified in the attribute
    """

    def _getattr(self, state, node):
        if callable(self.attr):
            return self.attr(node)
        else:
            return getattr(node, self.attr)

    def __call__(self, visitor, state, node):
        for chunk in self.resolve(
                visitor, state, node, self._getattr(state, node)):
            yield chunk


class Text(Token):
    """
    Simply leverage the state object for generating the rendering of
    the value required.
    """

    def __call__(self, visitor, state, node):
        for chunk in self.resolve(visitor, state, node, self.value):
            yield chunk


class JoinAttr(Attr):
    """
    Join the attr with value.
    """

    def __call__(self, visitor, state, node):
        nodes = iter(self._getattr(state, node))

        try:
            target_node = next(nodes)
        except StopIteration:
            return

        for chunk in self.resolve(visitor, state, node, target_node):
            yield chunk

        for target_node in nodes:
            # note that self.value is to be defined in the definition
            # format also.
            for value_node in visitor(state, node, self.value):
                yield value_node
            for chunk in self.resolve(visitor, state, node, target_node):
                yield chunk


class Optional(Token):
    """
    Optional text, depending on the node having an attribute

    attr
        the attr that is required for the statement to execute
    value
        the token definition segment to be executed
    """

    def __call__(self, visitor, state, node):
        if getattr(node, self.attr) is None:
            return

        # note that self.value is to be defined in the definition
        # format also.
        for chunk in visitor(state, node, self.value):
            yield chunk


class Operator(Attr):
    """
    An operator symbol.
    """

    # TODO figure out how to yield it in a way that tags this as an
    # operator, so that it can be properly normalized by the state base
    # tracker class. (i.e. no space before ':' but after, no space
    # between + iff not followed by unary +/++)

    def _getattr(self, state, node):
        if self.attr:
            return getattr(node, self.attr)
        else:
            return self.value
