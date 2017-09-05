# -*- coding: utf-8 -*-
"""
Various helpers for plugging into the pprint walker.

Combining the following layout handlers with the ruletypes definition
and pprint framework can be done in myriad of ways such that new output
formats can be constructed very trivially by simply changing how or what
of the following layouts to use to plug into the unparser walker setup.
"""

from __future__ import unicode_literals

import re

from calmjs.parse.asttypes import (
    Identifier,
    If,
    For,
    ForIn,
    While,
)
from calmjs.parse.ruletypes import (
    SourceChunk,

    Space,
    OptionalSpace,
    Newline,
    OptionalNewline,
    Indent,
    Dedent,
)

required_space = re.compile(r'^(?:\w\w|\+\+|\-\-)$')

# the various assignments symbols; for dealing with pretty spacing
assignment_tokens = {
    '*=', '/=', '%=', '+=', '-=', '<<=', '>>=', '>>>=', '&=', '^=', '|=', '='}
# other symbols
optional_rhs_space_tokens = {';', ')', None}


def rule_handler_noop(*a, **kw):
    # a no op for layouts
    return iter(())


def token_handler_str_default(token, dispatcher, node, subnode):
    # TODO the mangler could provide an implementation of this that will
    # fill out the last element of the yielded tuple.
    if isinstance(token.pos, int):
        _, lineno, colno = node.getpos(subnode, token.pos)
    else:
        lineno, colno = None, None
    yield SourceChunk(subnode, lineno, colno, None)


def token_handler_unobfuscate(token, dispatcher, node, subnode):
    """
    A token handler that will resolve and return the original identifier
    value.
    """

    original = (
        node.value
        if isinstance(node, Identifier) and node.value != subnode else
        None
    )

    if isinstance(token.pos, int):
        _, lineno, colno = node.getpos(original or subnode, token.pos)
    else:
        lineno, colno = None, None

    yield SourceChunk(subnode, lineno, colno, original)


def layout_handler_space_imply(dispatcher, node, before, after, prev):
    # default layout handler where the space will be rendered, with the
    # line/column set to 0 for sourcemap to generate the implicit value.
    yield SourceChunk(' ', 0, 0, None)


def layout_handler_space_drop(dispatcher, node, before, after, prev):
    # default layout handler where the space will be rendered, with the
    # line/column set to None for sourcemap to terminate the position.
    yield SourceChunk(' ', None, None, None)


def layout_handler_newline_simple(dispatcher, node, before, after, prev):
    # simply render the newline with an implicit sourcemap line/col
    yield SourceChunk(dispatcher.newline_str, 0, 0, None)


def layout_handler_newline_optional_pretty(
        dispatcher, node, before, after, prev):
    # simply render the newline with an implicit sourcemap line/col, if
    # not already preceded or followed by a newline
    l = len(dispatcher.newline_str)

    def fc(s):
        return '' if s is None else s[:l]

    def lc(s):
        return '' if s is None else s[-l:]

    # include standard ones plus whatever else that was provided, i.e.
    # the typical <CR><LF>
    newline_strs = {'\r', '\n', dispatcher.newline_str}

    if lc(before) in '\r\n':
        # not needed since this is the beginning
        return
    # if no new lines in any of the checked characters
    if not newline_strs & {lc(before), fc(after), lc(prev)}:
        yield SourceChunk(dispatcher.newline_str, 0, 0, None)


def layout_handler_space_optional_pretty(
        dispatcher, node, before, after, prev):
    if isinstance(node, (If, For, ForIn, While)):
        if after not in optional_rhs_space_tokens:
            yield SourceChunk(' ', 0, 0, None)
            return

    if before is None or after is None:
        # nothing.
        return
    s = before[-1:] + after[:1]

    if required_space.match(s) or after in assignment_tokens:
        yield SourceChunk(' ', 0, 0, None)
        return


def layout_handler_space_minimum(dispatcher, node, before, after, prev):
    if before is None or after is None:
        # nothing.
        return
    s = before[-1:] + after[:1]
    if required_space.match(s):
        yield SourceChunk(' ', 0, 0, None)


def default_rules():
    return {'layout_handlers': {
        Space: layout_handler_space_imply,
        OptionalSpace: layout_handler_space_optional_pretty,
        Newline: layout_handler_newline_simple,
        OptionalNewline: layout_handler_newline_optional_pretty,
        # if an indent is immediately followed by dedent without actual
        # content, simply do nothing.
        (Indent, Newline, Dedent): rule_handler_noop,
    }}


def minimum_rules():
    return {'layout_handlers': {
        Space: layout_handler_space_minimum,
        OptionalSpace: layout_handler_space_minimum,
    }}
