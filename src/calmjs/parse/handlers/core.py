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
    StreamFragment,

    OpenBlock,
    CloseBlock,
    EndStatement,
    Space,
    OptionalSpace,
    RequiredSpace,
    Newline,
    OptionalNewline,
    Indent,
    Dedent,
    LineComment as RuleTypeLineComment,
    BlockComment as RuleTypeBlockComment,
)
from calmjs.parse.lexers.es5 import PATT_LINE_CONTINUATION

required_space = re.compile(r'^(?:\w\w|\+\+|\-\-|\w\$|\$\w)$')

# the various assignments symbols; for dealing with pretty spacing
assignment_tokens = {
    '*=', '/=', '%=', '+=', '-=', '<<=', '>>=', '>>>=', '&=', '^=', '|=', '='}
# other symbols
optional_rhs_space_tokens = {';', ')', None}
space_imply = StreamFragment(' ', 0, 0, None, None)
space_drop = StreamFragment(' ', None, None, None, None)


def rule_handler_noop(*a, **kw):
    # a no op for layouts
    return
    yield  # pragma: no cover


def token_handler_str_default(
        token, dispatcher, node, subnode, sourcepath_stack=(None,)):
    """
    Standard token handler that will return the value, ignoring any
    tokens or strings that have been remapped.
    """

    if isinstance(token.pos, int):
        _, lineno, colno = node.getpos(subnode, token.pos)
    else:
        lineno, colno = None, None
    yield StreamFragment(subnode, lineno, colno, None, sourcepath_stack[-1])


def token_handler_unobfuscate(
        token, dispatcher, node, subnode, sourcepath_stack=(None,)):
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

    yield StreamFragment(
        subnode, lineno, colno, original, sourcepath_stack[-1])


def layout_handler_semicolon(dispatcher, node, before, after, prev):
    # required layout handler for the EndStatement Format rule.
    _, lineno, colno = node.getpos(';', 0)
    yield StreamFragment(';', lineno, colno, None, None)


def layout_handler_semicolon_optional(dispatcher, node, before, after, prev):
    # only yield if there is something after
    if after:
        _, lineno, colno = node.getpos(';', 0)
        yield StreamFragment(';', lineno, colno, None, None)


def layout_handler_openbrace(dispatcher, node, before, after, prev):
    # required layout handler for the OpenBlock Format rule.
    _, lineno, colno = node.getpos('{', 0)
    yield StreamFragment('{', lineno, colno, None, None)


def layout_handler_closebrace(dispatcher, node, before, after, prev):
    # required layout handler for the CloseBlock Format rule.
    _, lineno, colno = node.getpos('}', 0)
    yield StreamFragment('}', lineno, colno, None, None)


def layout_handler_space_imply(dispatcher, node, before, after, prev):
    # default layout handler where the space will be rendered, with the
    # line/column set to 0 for sourcemap to generate the implicit value.
    yield space_imply


def layout_handler_space_drop(dispatcher, node, before, after, prev):
    # default layout handler where the space will be rendered, with the
    # line/column set to None for sourcemap to terminate the position.
    yield space_drop


def layout_handler_newline_simple(dispatcher, node, before, after, prev):
    # simply render the newline with an implicit sourcemap line/col
    yield StreamFragment(dispatcher.newline_str, 0, 0, None, None)


def layout_handler_newline_optional_pretty(
        dispatcher, node, before, after, prev):
    # simply render the newline with an implicit sourcemap line/col, if
    # not already preceded or followed by a newline
    idx = len(dispatcher.newline_str)

    def fc(s):
        return '' if s is None else s[:idx]

    def lc(s):
        return '' if s is None else s[-idx:]

    # include standard ones plus whatever else that was provided, i.e.
    # the typical <CR><LF>
    newline_strs = {'\r', '\n', dispatcher.newline_str}

    if lc(before) in '\r\n':
        # not needed since this is the beginning
        return
    # if no new lines in any of the checked characters
    if not newline_strs & {lc(before), fc(after), lc(prev)}:
        yield StreamFragment(dispatcher.newline_str, 0, 0, None, None)


def layout_handler_space_optional_pretty(
        dispatcher, node, before, after, prev):
    if isinstance(node, (If, For, ForIn, While)):
        if after not in optional_rhs_space_tokens:
            yield space_imply
            return

    if before is None or after is None:
        # nothing.
        return
    s = before[-1:] + after[:1]

    if required_space.match(s) or after in assignment_tokens:
        yield space_imply
        return


def layout_handler_space_minimum(dispatcher, node, before, after, prev):
    if before is None or after is None:
        # nothing.
        return
    s = before[-1:] + after[:1]
    if required_space.match(s):
        yield space_imply


def deferrable_handler_literal_continuation(dispatcher, node):
    # assume the es5 method will continue to work.
    return PATT_LINE_CONTINUATION.sub('', node.value)


def deferrable_handler_comment(dispatcher, node):
    # simply return the value
    return node.value


def default_rules():
    return {'layout_handlers': {
        OpenBlock: layout_handler_openbrace,
        CloseBlock: layout_handler_closebrace,
        EndStatement: layout_handler_semicolon,
        Space: layout_handler_space_imply,
        OptionalSpace: layout_handler_space_optional_pretty,
        RequiredSpace: layout_handler_space_imply,
        Newline: layout_handler_newline_simple,
        OptionalNewline: layout_handler_newline_optional_pretty,
        # define these as noop so they can be normalized
        Indent: rule_handler_noop,
        Dedent: rule_handler_noop,
        # if an indent is immediately followed by dedent without actual
        # content, simply do nothing.
        (Indent, Newline, Dedent): rule_handler_noop,
        (OptionalSpace, EndStatement): layout_handler_semicolon,
    }, 'deferrable_handlers': {
        RuleTypeLineComment: deferrable_handler_comment,
        RuleTypeBlockComment: deferrable_handler_comment,
    }}


def minimum_rules():
    return {'layout_handlers': {
        OpenBlock: layout_handler_openbrace,
        CloseBlock: layout_handler_closebrace,
        EndStatement: layout_handler_semicolon,
        Space: layout_handler_space_minimum,
        OptionalSpace: layout_handler_space_minimum,
        RequiredSpace: layout_handler_space_imply,
        # drop the space before '{'
        (Space, OpenBlock): layout_handler_openbrace,
        # remove space before ';' for empty for statement
        (Space, EndStatement): layout_handler_semicolon,
        (OptionalSpace, EndStatement): layout_handler_semicolon,
    }}
