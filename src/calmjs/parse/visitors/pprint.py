# -*- coding: utf-8 -*-
"""
Base pretty printing state and visitor function.
"""

from calmjs.parse.pptypes import Token


class PrettyPrintState(object):
    """
    Pretty Printer State base class.

    A skeletal implementation that accept a mapping between the types
    that was reported as a subnode of a given node, and the function
    that is to be used to handle that, along with the definitions for
    building the pretty printed rendering output for every type as
    identified by their name, which the pptypes Token subclasses may
    use for lookup (i.e. state[Node]).

    Instances of this class is also used as the state object for
    tracking an execution of a pretty printing iteration.
    """

    def __init__(self, handlers, definitions):
        self.__handlers = {}
        self.__handlers.update(handlers)
        self.__definitions = {}
        self.__definitions.update(definitions)

    def __getitem__(self, key):
        # TODO figure out how to do proper lookup by the type, rather
        # than this string hack.
        return self.__definitions[key.__class__.__name__]

    def __call__(self, node, subnode, token):
        handler = self.__handlers.get(type(subnode))
        if handler:
            for chunk in handler(self, node, subnode, token):
                yield chunk
        else:
            # TODO raise this with a reason as to why/how did this
            # happen.
            raise NotImplementedError


def pretty_print_visitor(state, node, definition):
    """
    The default, standalone visitor function following the standard
    argument format, where the first argument is a PrettyPrintState,
    second being the node, third being the definition tuple to follow
    from for generating a rendering of the node.

    While the state object is able to provide the lookup directly, this
    extra definition argument allow more flexibility in having Token
    subtypes being able to provide specific definitions also that may
    be required, such as the generation of optional rendering output.
    """

    for rule in definition:
        if isinstance(rule, Token):
            gen = rule(pretty_print_visitor, state, node)
        else:
            gen = state(node, rule, rule)
        # TODO process Tokens first; so that the first chunk from the
        # following token can be used for the Layout rules which is
        # managed by the state object.
        for chunk in gen:
            # e.g.
            # last_chunk = chunk
            yield chunk


# the various output generation - when changing output, no more having
# to expend effort to write an entire new visitor class or modify every
# visit_* methods ever again.

def node_handler_null(state, node, subnode, token):
    return iter([])


def node_handler_str_default(state, node, subnode, token):
    if isinstance(token.pos, int):
        _, lineno, colno = node.getpos(subnode, token.pos)
    else:
        lineno, colno = None, None
    yield (subnode, lineno, colno, None)


def node_handler_space_imply(state, node, subnode, token):
    yield (' ', 0, 0, None)


def node_handler_space_drop(state, node, subnode, token):
    yield (' ', None, None, None)


def node_handler_newline_simple(state, node, subnode, token):
    yield ('\n', 0, 0, None)
