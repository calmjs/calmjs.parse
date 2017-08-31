# -*- coding: utf-8 -*-
"""
Classes for achieving the name mangling effect.
"""

import logging

from calmjs.parse.ruletypes import PushScope
from calmjs.parse.ruletypes import PopScope
from calmjs.parse.ruletypes import Declare
from calmjs.parse.ruletypes import Resolve
from calmjs.parse.layout import rule_handler_noop

from calmjs.parse.unparsers.walker import Dispatcher
from calmjs.parse.unparsers.walker import walk

logger = logging.getLogger(__name__)
logger.level = logging.WARNING


class Scope(object):
    """
    For tracking the symbols.
    """

    def __init__(self, node, parent=None):
        self.node = node
        self.parent = parent
        self.children = []

        # Local names is for this scope only, the variable name will be
        # the key, with a value of how many times it has been referenced
        # anywhere in this scope.
        self.referenced_symbols = {}

        # This is a set of names that have been declared (i.e. via var
        # or function)
        self.declared_symbols = set()

        # All symbols remapped to be remapped to a different name will
        # be stored here, for the resolved method to make use of.
        self.remapped_symbols = {}

    @property
    def global_symbols(self):
        """
        These are symbols that have been referenced, but not declared
        within this scope.
        """

        return set(
            s for s in self.referenced_symbols
            if s not in self.declared_symbols
        )

    def declare(self, symbol):
        self.declared_symbols.add(symbol)
        # simply create the reference, if not already there.
        self.referenced_symbols[symbol] = self.referenced_symbols.get(
            symbol, 0)

    def reference(self, symbol):
        # increment reference counter, declare one if not already did.
        self.referenced_symbols[symbol] = self.referenced_symbols.get(
            symbol, 0) + 1

    def resolve(self, symbol):
        return self.remapped_symbols.get(symbol, symbol)

    def nest(self, node):
        """
        Create a new nested scope that is within this instance, binding
        the provided node to it.
        """

        nested_scope = type(self)(node, self)
        self.children.append(nested_scope)
        return nested_scope


class Shortener(object):
    """
    The name shortener.
    """

    def __init__(self, use_global_scope=False):
        """
        Arguments

        global_scope
            Also have it affect global scope.  Do not enable this option
            unless there is an explicit need to do so as this may result
            in code that no longer function as expected.

            Defaults to False for the reason above.
        """

        # this is a mapping of Identifier nodes to the scope
        self.identifiers = {}
        self.scopes = {}
        self.stack = []
        # global scope is in the ether somewhere so it isn't exactly
        # bounded to anything.
        self.global_scope = Scope(None)
        self.stack.append(self.global_scope)

    @property
    def current_scope(self):
        return self.stack[-1]

    def push_scope(self, dispatcher, node, *a, **kw):
        scope = self.current_scope.nest(node)
        self.scopes[node] = scope
        self.stack.append(scope)

    def pop_scope(self, dispatcher, node, *a, **kw):
        self.stack.pop()
        # TODO figure out whether/how to check that the scope that just
        # got popped is indeed of this node.

    def declare(self, dispatcher, node):
        """
        Declare the value of the Identifier of the node that was passed
        in as used in the current scope.
        """

        self.current_scope.declare(node.value)

    def reference(self, dispatcher, node):
        """
        Register this identifier to the current scope.
        """

        # the identifier node itself will be mapped to the current scope
        # for the resolve to work
        self.identifiers[node] = self.current_scope
        self.current_scope.reference(node.value)

    def resolve(self, dispatcher, node):
        """
        For the given node, resolve it into the scope it was declared
        at, and if one was found, return its value.
        """

        scope = self.identifiers.get(node)
        if not scope:
            return node.value
        return scope.resolve(node.value)

    def build_substitutions(self, dispatcher, node):
        """
        This is for the Unparser to use as a prewalk hook.
        """

        local_dispatcher = Dispatcher(
            definitions=dict(dispatcher),
            token_handler=rule_handler_noop,
            layout_handlers={
                PushScope: self.push_scope,
                PopScope: self.pop_scope,
            },
            deferrable_handlers={
                Declare: self.declare,
                Resolve: self.reference,
            },
        )
        return list(walk(local_dispatcher, node))


def mangle(shorten_global=False):
    def shortener_rules():
        inst = Shortener(shorten_global)
        # XXX don't actually return this, but use these internally
        # for the first pass
        # second pass will only have a simple resolve.
        return {
            'deferrable_handlers': {
                Resolve: inst.resolve,
            },
            'prewalk_hooks': [
                inst.build_substitutions,
            ],
        }
    return shortener_rules
