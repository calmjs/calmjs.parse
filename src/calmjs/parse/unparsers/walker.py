# -*- coding: utf-8 -*-
"""
Base class and function for making a walk through a given asttypes tree
possible.
"""

from __future__ import unicode_literals

from calmjs.parse.asttypes import Node
from calmjs.parse.ruletypes import Token
from calmjs.parse.ruletypes import Structure
from calmjs.parse.ruletypes import Layout
from calmjs.parse.ruletypes import LayoutChunk


def optimize_structure_handler(rule, handler):
    """
    Produce an "optimized" version of handler for the dispatcher to
    limit reference lookups.
    """

    def runner(walk, dispatcher, node):
        handler(dispatcher, node)
        return
        yield  # pragma: no cover

    return runner


def optimize_layout_handler(rule, handler):
    """
    Produce an "optimized" version of handler for the dispatcher to
    limit reference lookups.
    """

    def runner(walk, dispatcher, node):
        yield LayoutChunk(rule, handler, node)

    return runner


class Dispatcher(object):
    """
    Provide storage and lookup for the stored definitions and the
    handlers, which is documented by the constructor below.

    The instances of this class will be a callable that accept a single
    argument; when called with an object, the handling function, if any,
    will be returned to achieve the generation of output chunks.

    Calling on an instance of this object with a Rule (typically either
    a Token instance, or a Layout type/class object) will return the
    associated handler that was set up initially for a given instance.

    Accessing via a Node type as a key will return the definition that
    was initially set up for a given instance.

    The default implementation also provide a couple properties for ease
    of layout customization, which are the indent character and the
    newline character.  As certain users and/or platforms expect certain
    character sequences for these outputs, they can be specified in the
    constructor for this class, or be completely ignored by the specific
    layout handlers.

    While this class can be used (it was originally conceived) as a
    generic object that allow arbitrary assignments of arguments for
    consumption by layout functions, it's better to have a dedicated
    class that provide instance methods that plug into this.  See the
    modules inside ``calmjs.parse.handlers`` for various examples on
    how this could be set up.  To better maintain object purity, users
    of this class should not assign additional attributes to instances
    of this class.
    """

    def __init__(
            self, definitions, token_handler,
            layout_handlers, deferrable_handlers,
            indent_str='  ', newline_str='\n'):
        """
        The constructor takes three arguments.

        definitions
            A mapping from the names of a Node to their definitions; a
            definition is a tuple of rules for describing how a
            particular Node should be rendered.  The Nodes are described
            in the asttypes module, while the Rules are described in the
            pptypes module.

        token_handler
            The handler that will deal with tokens.  It must be a
            callable that accepts four arguments

            token
                the token instance that will do the invocation
            dispatcher
                an instance of this class
            node
                a Node instance (from asttypes)
            value
                the value that was derived by the token based on its
                implementation.

        layout_handlers
            A map (dictionary) from Layout types to the handlers, which
            are callables that accepts these five arguments

            dispatcher
                an instance of this class
            node
                an asttypes.Node instance.
            before
                a value that was yielded by the previous token
            after
                a value to be yielded by the subsequent token
            prev
                the previously yielded layout token

        deferrable_handlers
            A map (dictionary) from Deferrable types to the handlers,
            which are callables that accepts these two arguments

            dispatcher
                an instance of this class
            node
                an asttypes.Node instance.

        indent_str
            The string used to indent a line with.  Default is '  '.
            This attribute will be provided as the property
            ``indent_str``.

        newline_str
            The string used for renderinga new line with.  Default is
            <LF> (line-feed, or '\\n').  This attribute will be provided
            as the property ``newline_str``.
        """

        self.__token_handler = token_handler
        self.__layout_handlers = {}
        self.__layout_handlers.update(layout_handlers)
        self.__deferrable_handlers = {}
        self.__deferrable_handlers.update(deferrable_handlers)
        self.__definitions = {}
        self.__definitions.update(definitions)
        self.__indent_str = indent_str
        self.__newline_str = newline_str

        self.__optimized_definitions = self.optimize()

    def optimize_definition(self, name, definition):
        rules = []
        for rule in definition:
            if isinstance(rule, type):
                if issubclass(rule, Structure):
                    handler = self.__layout_handlers.get(rule)
                    if handler:
                        rules.append(optimize_structure_handler(rule, handler))
                    continue
                elif issubclass(rule, Layout):
                    # a noop here so that the relevant chunk will be
                    # yielded for normalization by bulk-lookup.
                    handler = self.__layout_handlers.get(rule)
                    if handler:
                        rules.append(optimize_layout_handler(rule, handler))
                    continue
            if isinstance(rule, Token):
                value = (self.optimize_definition(
                    name, rule.value
                ) if isinstance(rule.value, tuple) else rule.value)
                rules.append(type(rule)(rule.attr, value, rule.pos))
                continue

            raise TypeError(
                "definition for '%s' contain unsupported rule (got: %r)" % (
                    name, rule))
        return rules

    def optimize(self):
        return {
            astname: self.optimize_definition(astname, definition)
            for astname, definition in self.__definitions.items()
        }

    def get_optimized_definition(self, node):
        """
        This is for getting at the definition for a particular asttype.
        """

        # The reason why the types were not used simply performance of
        # isisntance is bad, that the types are uniquely named, and that
        # they are always subclassed through the factory.  While working
        # at the type level is the correct method, the performance
        # penalties that it attracts however make this naive approach
        # more attractive.
        return self.__optimized_definitions[node.__class__.__name__]

    def __iter__(self):
        for item in self.__definitions.items():
            yield item

    def deferrable(self, rule):
        return self.__deferrable_handlers.get(type(rule), NotImplemented)

    def token(self, token, node, value, sourecepath_stack):
        if self.__token_handler:
            for fragment in self.__token_handler(
                    token, self, node, value, sourecepath_stack):
                yield fragment

    def layout(self, rule):
        """
        Get handler for this layout rule.
        """

        return self.__layout_handlers.get(rule, NotImplemented)

    @property
    def indent_str(self):
        return self.__indent_str

    @property
    def newline_str(self):
        return self.__newline_str


def walk(dispatcher, node, definition=None):
    """
    The default, standalone walk function following the standard
    argument ordering for the unparsing walkers.

    Arguments:

    dispatcher
        a Dispatcher instance, defined earlier in this module.  This
        instance will dispatch out the correct callable for the various
        object types encountered throughout this recursive function.

    node
        the starting Node from asttypes.

    definition
        a standalone definition tuple to start working on the node with;
        if none is provided, an initial definition will be looked up
        using the dispatcher with the node for the generation of output.

    While the dispatcher object is able to provide the lookup directly,
    this extra definition argument allow more flexibility in having
    Token subtypes being able to provide specific definitions also that
    may be required, such as the generation of optional rendering
    output.
    """

    # The inner walk function - this is actually exposed to the token
    # rule objects so they can also make use of it to process the node
    # with the dispatcher.

    nodes = []
    sourcepath_stack = [NotImplemented]

    def _walk(dispatcher, node, definition=None, token=None):
        if not isinstance(node, Node):
            for fragment in dispatcher.token(
                    token, nodes[-1], node, sourcepath_stack):
                yield fragment
            return

        push = bool(node.sourcepath)
        if push:
            sourcepath_stack.append(node.sourcepath)
        nodes.append(node)

        if definition is None:
            definition = dispatcher.get_optimized_definition(node)

        for rule in definition:
            for chunk in rule(_walk, dispatcher, node):
                yield chunk

        nodes.pop(-1)
        if push:
            sourcepath_stack.pop(-1)

    # Format layout markers are not handled immediately in the walk -
    # they will simply be buffered so that a collection of them can be
    # handled at once.
    def process_layouts(layout_rule_chunks, last_chunk, chunk):
        before_text = last_chunk.text if last_chunk else None
        after_text = chunk.text if chunk else None
        # the text that was yielded by the previous layout handler
        prev_text = None

        # While Layout rules in a typical definition are typically
        # interspersed with Tokens, certain assumptions with how the
        # Layouts are specified within there will fail when Tokens fail
        # to generate anything for any reason.  However, the dispatcher
        # instance will be able to accept and resolve a tuple of Layouts
        # to some handler function, so that a form of normalization can
        # be done.  For instance, an (Indent, Newline, Dedent) can
        # simply be resolved to no operations.  To achieve this, iterate
        # through the layout_rule_chunks and generate a normalized form
        # for the final handling to happen.

        # the preliminary stack that will be cleared whenever a
        # normalized layout rule chunk is generated.
        lrcs_stack = []

        # first pass: generate both the normalized/finalized lrcs.
        for lrc in layout_rule_chunks:
            lrcs_stack.append(lrc)

            # check every single chunk from left to right...
            for idx in range(len(lrcs_stack)):
                rule = tuple(lrc.rule for lrc in lrcs_stack[idx:])
                handler = dispatcher.layout(rule)
                if handler is not NotImplemented:
                    # not manipulating lrsc_stack from within the same
                    # for loop that it is being iterated upon
                    break
            else:
                # which continues back to the top of the outer for loop
                continue

            # So a handler is found from inside the rules; extend the
            # chunks from the stack that didn't get normalized, and
            # generate a new layout rule chunk.
            lrcs_stack[:] = lrcs_stack[:idx]
            lrcs_stack.append(LayoutChunk(
                rule, handler,
                layout_rule_chunks[idx].node,
            ))

        # second pass: now the processing can be done.
        for lr_chunk in lrcs_stack:
            gen = lr_chunk.handler(
                dispatcher, lr_chunk.node, before_text, after_text, prev_text)
            if not gen:
                continue
            for chunk_from_layout in gen:
                yield chunk_from_layout
                prev_text = chunk_from_layout.text

    # The top level walker implementation
    def walk():
        last_chunk = None
        layout_rule_chunks = []

        for chunk in _walk(dispatcher, node, definition):
            if isinstance(chunk, LayoutChunk):
                layout_rule_chunks.append(chunk)
            else:
                # process layout rule chunks that had been cached.
                for chunk_from_layout in process_layouts(
                        layout_rule_chunks, last_chunk, chunk):
                    yield chunk_from_layout
                layout_rule_chunks[:] = []
                yield chunk
                last_chunk = chunk

        # process the remaining layout rule chunks.
        for chunk_from_layout in process_layouts(
                layout_rule_chunks, last_chunk, None):
            yield chunk_from_layout

    for chunk in walk():
        yield chunk
