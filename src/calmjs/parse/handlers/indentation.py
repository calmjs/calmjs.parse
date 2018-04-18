# -*- coding: utf-8 -*-
"""
Layout handlers for building indentation.
"""

from calmjs.parse.ruletypes import (
    Dedent,
    Indent,
    Newline,
    OptionalNewline,
    StreamFragment,
    OpenBlock,
    CloseBlock,
    EndStatement,
)
from calmjs.parse.handlers.core import (
    layout_handler_semicolon,
    layout_handler_openbrace,
    layout_handler_closebrace,
)


class Indentator(object):
    """
    For tracking indent/dedents.
    """

    def __init__(self, indent_str=None):
        """
        Arguments

        indent_str
            The string to do indentation with; defaults to use whatever
            provided by the dispatcher.
        """
        self.indent_str = indent_str
        self._level = 0

    def layout_handler_indent(self, dispatcher, node, before, after, prev):
        self._level += 1

    def layout_handler_dedent(self, dispatcher, node, before, after, prev):
        self._level -= 1

    def _generate_indents(self, dispatcher):
        s = self.indent_str if self.indent_str else dispatcher.indent_str
        indents = s * self._level
        if indents:
            yield StreamFragment(indents, None, None, None, None)

    def layout_handler_newline(self, dispatcher, node, before, after, prev):
        # simply render the newline with an implicit sourcemap line/col
        yield StreamFragment(dispatcher.newline_str, 0, 0, None, None)
        for chunk in self._generate_indents(dispatcher):
            yield chunk

    def layout_handler_newline_optional(
            self, dispatcher, node, before, after, prev):
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

        if (before and lc(before) in '\r\n'):
            # not needed since this is the beginning
            return
        # if no new lines in any of the checked characters
        if not newline_strs & {lc(before), fc(after), lc(prev)}:
            yield StreamFragment(dispatcher.newline_str, 0, 0, None, None)

        for chunk in self._generate_indents(dispatcher):
            yield chunk


def indent(indent_str=None):
    """
    An example indentation ruleset.
    """

    def indentation_rule():
        inst = Indentator(indent_str)
        return {'layout_handlers': {
            Indent: inst.layout_handler_indent,
            Dedent: inst.layout_handler_dedent,
            Newline: inst.layout_handler_newline,
            OptionalNewline: inst.layout_handler_newline_optional,
            OpenBlock: layout_handler_openbrace,
            CloseBlock: layout_handler_closebrace,
            EndStatement: layout_handler_semicolon,
        }}
    return indentation_rule
