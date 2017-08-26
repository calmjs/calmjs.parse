# -*- coding: utf-8 -*-
"""
ES5 base visitors
"""

from calmjs.parse.ruletypes import (
    Space,
    OptionalSpace,
    Newline,
    OptionalNewline,
    Indent,
    Dedent,
)
from calmjs.parse.unparsers.prettyprint import (
    State,
    visitor,
)
from calmjs.parse.layout import (
    rule_handler_noop,
    token_handler_str_default,
    layout_handler_space_imply,
    layout_handler_newline_optional_pretty,
    layout_handler_newline_simple,
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,
)


def default_layout_handlers():
    return {
        Space: layout_handler_space_imply,
        OptionalSpace: layout_handler_space_optional_pretty,
        Newline: layout_handler_newline_simple,
        OptionalNewline: layout_handler_newline_optional_pretty,
        # if an indent is immediately followed by dedent without actual
        # content, simply do nothing.
        (Indent, Newline, Dedent): rule_handler_noop,
    }


def minimum_layout_handlers():
    return {
        Space: layout_handler_space_minimum,
        OptionalSpace: layout_handler_space_minimum,
    }


class BaseUnparser(object):
    """
    A simple base visitor class built upon the prettyprint and layout
    helper classes.
    """

    def __init__(
            self,
            definitions,
            token_handler=token_handler_str_default,
            layouts=(default_layout_handlers,),
            layout_handlers=None,
            visitor=visitor,
            state_cls=State):
        """
        Optional arguements

        definition
            The definition for unparsing.
        token_handler
            passed onto the state object; this is the handler that will
            process
        layouts
            An tuple of callables that will provide the setup of
            indentation.  The callables must return a layout_handlers
            mapping, which is a dict with the key being the layout class
            and the value being the callable that accept a
            State instance, a Node, before and after chunk.
        layout_handlers
            Additional layout handlers, given in the mapping that was
            described above.
        visitor
            The visitor function - defaults to the version from the
            prettyprint module
        state_cls
            The State class - defaults to the version from the
            prettyprint module
        """

        self.token_handler = token_handler
        self.layout_handlers = {}
        for layout in layouts:
            self.layout_handlers.update(layout())
        if layout_handlers:
            self.layout_handlers.update(layout_handlers)
        self.definitions = {}
        self.definitions.update(definitions)
        self.visitor = visitor
        self.state_cls = state_cls

    def __call__(self, node):
        state = self.state_cls(
            self.definitions, self.token_handler, self.layout_handlers)
        for chunk in self.visitor(state, node, state[node]):
            yield chunk
