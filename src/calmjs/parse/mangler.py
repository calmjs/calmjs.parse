# -*- coding: utf-8 -*-
"""
Classes for achieving the name mangling effect.
"""

import logging

from calmjs.parse.ruletypes import PushScope
from calmjs.parse.ruletypes import PopScope
from calmjs.parse.ruletypes import Declare
from calmjs.parse.ruletypes import Resolve

from calmjs.parse.unparsers.walker import Dispatcher
from calmjs.parse.unparsers.walker import walk

logger = logging.getLogger(__name__)
logger.level = logging.WARNING


class Scope(object):
    """
    For tracking the symbols.
    """

    def __init__(self, node, parent):
        self.node = node
        self.parent = parent

        # This is for tracking _every_ variable name that has been used
        # ever within all the scopes within this graph (well, tree).  To
        # achieve that, just simply reuse the reference of the parent.
        if parent:
            self.consumed_symbols = parent.consumed_symbols
        else:
            self.consumed_symbols = set()

        # Local names is for this scope only, the variable name will be
        # the key, with a value of how many times it has been referenced
        # anywhere in this scope.
        self.referenced_symbols = {}

        # This is a set of names that have been declared (i.e. via var
        # or function)
        self.local_symbols = set()

    def declare(self, symbol):
        self.consumed_symbols.add(symbol)
        self.local_symbols.add(symbol)
        # simply create the reference.
        self.referenced_symbols[symbol] = self.referenced_symbols.get(
            symbol, 0)

    def resolve(self, symbol):
        self.referenced_symbols[symbol] = self.referenced_symbols.get(
            symbol, 0) + 1


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

        self.scopes = {}
        self.stack = []
        self.stack.append(Scope(None, None))

    @property
    def current_scope(self):
        return self.stack[-1]

    def register(self, dispatcher, node):
        """
        Register this identifier to the current scope.
        """

        if self.current_scope:
            pass

    # XXX the first pass will push the scope
    # the variable adding will have a node looking up its scope
    # the resolution step will just do that.
    # first pass will do the push/pop, along with resolve for counting
    # second pass will only have resolve to actual token
    def push_scope(self, dispatcher, node, *a, **kw):
        scope = Scope(node, self.current_scope)
        self.scopes[node] = scope
        self.stack.append(scope)

    def pop_scope(self, dispatcher, node, *a, **kw):
        self.stack.pop()
        # TODO figure out whether/how to check that the scope that just
        # got popped is indeed of this node.

    def declare(self, dispatcher, node):
        self.current_scope.declare(node.value)

    def resolve(self, dispatcher, node):
        # this is for the first run - it will produce no data and that
        # should be fine.
        return self.current_scope.resolve(node.value)

    def create_scope_lookup_tables(self, dispatcher, node):
        """
        This is for the Unparser to use as a prewalk hook.
        """

        def null_token_handler(token, dispatcher, node, subnode):
            return iter([])

        local_dispatcher = Dispatcher(
            definitions=dict(dispatcher),
            token_handler=null_token_handler,
            layout_handlers={
                PushScope: self.push_scope,
                PopScope: self.pop_scope,
            },
            deferred_handlers={
                Declare: self.declare,
                Resolve: self.register,
            },
        )
        list(walk(local_dispatcher, node))


def mangle(shorten_global=False):
    def shortener_rules():
        inst = Shortener(shorten_global)
        # XXX don't actually return this, but use these internally
        # for the first pass
        # second pass will only have a simple resolve.
        return {
            'deferred_handlers': {
                Resolve: inst.resolve,
            },
            'prewalk_hooks': [
                inst.create_scope_lookup_tables,
            ],
        }
    return shortener_rules