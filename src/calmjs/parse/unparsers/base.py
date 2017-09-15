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
from calmjs.parse.sourcemap import write
from calmjs.parse.sourcemap import write_sourcemap

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

    def write(
            self, node, output_stream, sourcemap_stream=None,
            sourcemap_normalize_mappings=True,
            sourcemap_normalize_paths=True):
        """
        Write out the node into the output stream.  If file objects are
        passed in as the *_stream arguments and if sources and target
        arguments are unspecified, the names of those file objects will
        be used to derive the sources and target.  If they are opened
        using absolute paths, the sourcemap generated will have its
        paths normalized to relative paths.

        If the provided streams are not anchored on the filesystem, or
        that the provide node was generated from a string or in-memory
        stream, the generation of the sourcemap should be done using the
        lower level `write` function provided by the sourcemap module,
        which this method wraps.  Alternatively, the top level node
        should have its sourcepath set to path that this node originated
        from.

        Arguments

        node
            The Node to write with.
        output_stream
            The stream object to write to; its 'write' method will be
            invoked.
        sourcemap_stream
            If one is provided, the sourcemap will be written out to it.
        sourcemap_normalize_mappings
            Flag for the normalization of the sourcemap mappings;
            Defaults to True to enable a reduction in output size.
        sourcemap_normalize_paths
            If set to true, all absolute paths will be converted to the
            relative form when the sourcemap is generated, if all paths
            provided are in the absolute form.

            Defaults to True to enable a reduction in output size.
        """

        # TODO if there is a custom instance of bookkeeping class,
        # check that multiple input nodes from different source files
        # can be merged into one.
        mappings, sources, names = write(
            self(node), output_stream, normalize=sourcemap_normalize_mappings)
        if sourcemap_stream:
            write_sourcemap(
                mappings, sources, names, output_stream, sourcemap_stream,
                normalize_paths=sourcemap_normalize_paths,
            )

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
