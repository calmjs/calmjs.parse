# -*- coding: utf-8 -*-
"""
Base unparser implementation

Brings together the different bits from the different helpers.
"""

from __future__ import unicode_literals

import logging

from calmjs.parse.unparsers.walker import (
    Dispatcher,
    walk,
)
from calmjs.parse.handlers.core import default_rules
from calmjs.parse.handlers.core import token_handler_str_default

logger = logging.getLogger(__name__)


class BaseUnparser(object):
    """
    A simple base class for gluing together the default Dispatcher and
    walk function together to achieve unparsing.
    """

    def __init__(
            self,
            definitions,
            token_handler=None,
            rules=(default_rules,),
            layout_handlers=None,
            deferrable_handlers=None,
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
            the mappings for layout_handlers and deferrable_handlers.
        layout_handlers
            Additional layout handlers for the Dispatcher instance.
        deferrable_handlers
            Additional deferrable handlers for the Dispatcher instance.
        prewalk_hooks
            A list of callables that will be called before the walk
            function is called.  The dispatcher instance and the node
            that was called on will be passed to these callables.
        walk
            The walk function - defaults to the version from the walker
            module
        dispatcher_cls
            The Dispatcher class - defaults to the version from the
            walker module
        """

        self.layout_handlers = {}
        self.deferrable_handlers = {}
        self.prewalk_hooks = []
        self.token_handler = None

        # TODO should probably invoke these at the __call__
        for rule in rules:
            r = rule()
            if r.get('token_handler'):
                if self.token_handler:
                    logger.warning(
                        "rule '%s' specified a new token_handler '%s', "
                        "overriding previously assigned token_handler '%s'",
                        rule.__name__, r['token_handler'].__name__,
                        self.token_handler.__name__,
                    )
                else:
                    logger.debug(
                        "rule '%s' specified a token_handler '%s'",
                        rule.__name__, r['token_handler'].__name__,
                    )
                self.token_handler = r['token_handler']
            self.layout_handlers.update(r.get('layout_handlers', {}))
            self.deferrable_handlers.update(r.get('deferrable_handlers', {}))
            self.prewalk_hooks.extend(r.get('prewalk_hooks', []))

        if token_handler:
            if self.token_handler and self.token_handler is not token_handler:
                logger.info(
                    "provided token_handler '%s' to the '%s' instance "
                    "will override rule derived token_handler '%s'",
                    token_handler.__name__, self.__class__.__name__,
                    self.token_handler.__name__
                )
            else:
                logger.debug(
                    "'%s' using provided token_handler '%s'; ",
                    self.__class__.__name__, token_handler.__name__
                )
            self.token_handler = token_handler
        elif token_handler is None and self.token_handler is None:
            self.token_handler = token_handler_str_default
            logger.debug(
                "'%s' instance has no token_handler specified; "
                "default handler '%s' activated",
                self.__class__.__name__, self.token_handler.__name__
            )

        if layout_handlers:
            self.layout_handlers.update(layout_handlers)

        if deferrable_handlers:
            self.deferrable_handlers.update(deferrable_handlers)

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
            self.deferrable_handlers,
        )

        for prewalk_hook in self.prewalk_hooks:
            node = prewalk_hook(dispatcher, node)

        for chunk in self.walk(dispatcher, node):
            yield chunk
