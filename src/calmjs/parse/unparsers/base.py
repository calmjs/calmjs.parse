# -*- coding: utf-8 -*-
"""
Base unparser implementation

Brings together the different bits from the different helpers.
"""

from calmjs.parse.ruletypes import (
    Space,
    OptionalSpace,
    Newline,
    OptionalNewline,
    Indent,
    Dedent,
)
from calmjs.parse.unparsers.walker import (
    Dispatcher,
    walk,
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
    return {'layout_handlers': {
        Space: layout_handler_space_imply,
        OptionalSpace: layout_handler_space_optional_pretty,
        Newline: layout_handler_newline_simple,
        OptionalNewline: layout_handler_newline_optional_pretty,
        # if an indent is immediately followed by dedent without actual
        # content, simply do nothing.
        (Indent, Newline, Dedent): rule_handler_noop,
    }}


def minimum_layout_handlers():
    return {'layout_handlers': {
        Space: layout_handler_space_minimum,
        OptionalSpace: layout_handler_space_minimum,
    }}


class BaseUnparser(object):
    """
    A simple base class for gluing together the default Dispatcher and
    walk function together to achieve unparsing.
    """

    def __init__(
            self,
            definitions,
            token_handler=token_handler_str_default,
            rules=(default_layout_handlers,),
            layout_handlers=None,
            deferred_handlers=None,
            prewalk_hooks=(),
            walk=walk,
            dispatcher_cls=Dispatcher):
        """
        Optional arguements

        definition
            The definition for unparsing.
        token_handler
            passed onto the dispatcher object; this is the handler that
            will process the token in to chunks.
        rules
            A tuple of callables that will set up the various rules that
            will be passed to the dispatcher instance.  It should return
            the mappings for layout_handlers and deferred_handlers.
        layout_handlers
            Additional layout handlers for the Dispatcher instance.
        deferred_handlers
            Additional deferred handlers for the Dispatcher instance.
        walk
            The walk function - defaults to the version from the walker
            module
        dispatcher_cls
            The Dispatcher class - defaults to the version from the
            walker module
        """

        self.token_handler = token_handler
        self.layout_handlers = {}
        self.deferred_handlers = {}
        self.prewalk_hooks = []

        for rule in rules:
            r = rule()
            self.layout_handlers.update(r.get('layout_handlers', {}))
            self.deferred_handlers.update(r.get('deferred_handlers', {}))
            self.prewalk_hooks.extend(r.get('prewalk_hooks', []))

        if layout_handlers:
            self.layout_handlers.update(layout_handlers)

        if deferred_handlers:
            self.deferred_handlers.update(deferred_handlers)

        if prewalk_hooks:
            self.prewalk_hooks.extend(prewalk_hooks)

        self.definitions = {}
        self.definitions.update(definitions)
        self.walk = walk
        self.dispatcher_cls = dispatcher_cls

    def __call__(self, node):
        dispatcher = self.dispatcher_cls(
            self.definitions,
            self.token_handler,
            self.layout_handlers,
            self.deferred_handlers,
        )

        for prewalk_hook in self.prewalk_hooks:
            prewalk_hook(dispatcher, node)

        for chunk in self.walk(dispatcher, node):
            yield chunk
