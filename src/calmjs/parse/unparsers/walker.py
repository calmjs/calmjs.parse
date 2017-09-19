# -*- coding: utf-8 -*-
"""
Base class and function for making a walk through a given asttypes tree
possible.
"""

from __future__ import unicode_literals

from collections import Iterable
from itertools import chain
from calmjs.parse.ruletypes import Token
from calmjs.parse.ruletypes import Structure
from calmjs.parse.ruletypes import Layout
from calmjs.parse.ruletypes import LayoutChunk
from calmjs.parse.ruletypes import StreamFragment
from calmjs.parse.ruletypes import TextChunk

# the default noop.
from calmjs.parse.handlers.core import rule_handler_noop


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

    def __iter__(self):
        for item in self.__definitions.items():
            yield item

    def __getitem__(self, key):
        """
        This is for getting at the definition for a particular asttype.
        """

        # TODO figure out how to do lookup by the type itself directly,
        # rather than this string hack.
        # The reason why the types were not used simply because it would
        # be a bit annoying to deal with subclasses, as resolution will
        # have to be done for the parent class, given that asttypes are
        # always subclassed.  While working with types directly is the
        # correct way to handle that, it is however rather complicated
        # for this particular goal when this naive solution achieves the
        # goal without too much issues.
        return self.__definitions[key.__class__.__name__]

    def deferrable(self, rule):
        return self.__deferrable_handlers.get(type(rule), NotImplemented)

    def layout_chunk(self, rule, node):
        handler = self.__layout_handlers.get(rule, rule_handler_noop)
        if issubclass(rule, Structure):
            # A stucture layout marker; these will be actioned
            # immediately as it relates to the handling of the
            # structural description of the asttype at the current
            # point.
            if handler:
                handler(self, node)
            return
        elif issubclass(rule, Layout):
            # Since Layouts can be batch processed, defer action by
            # yielding a LayoutChunk as a marker so that the option to
            # batch process a sequence of Layouts as a single step can
            # be done.  If the handler is not registered to the
            # dispatcher, also yield the rule attached to a noop handler
            # so that it won't be omitted in the batch handling.
            yield LayoutChunk(rule, handler, node)

    def __call__(self, rule):
        """
        This is to find a callable for the particular rule encountered.
        """

        # this is really starting to look like a multi-dispatcher,
        # especially if it can accept multiple arguments to invoke the
        # located callable in one go with the arguments supplied here.

        if isinstance(rule, Token):
            return self.__token_handler
        else:
            return self.__layout_handlers.get(rule, NotImplemented)

    @property
    def indent_str(self):
        return self.__indent_str

    @property
    def newline_str(self):
        return self.__newline_str


def textchunk_to_streamfragment(textchunk, source=None):
    return StreamFragment(
        text=textchunk.text,
        lineno=textchunk.lineno,
        colno=textchunk.colno,
        name=textchunk.original,
        source=source,
    )


def walk_stacktracking_streamfragment(walk):
    sourcepath_stack = [NotImplemented]

    def _walk(dispatcher, node, definition=None):
        pushed = False
        if node.sourcepath:
            pushed = True
            sourcepath_stack.append(node.sourcepath)

        for chunk in walk(dispatcher, node, definition=definition):
            if isinstance(chunk, TextChunk):
                yield textchunk_to_streamfragment(chunk, sourcepath_stack[-1])
            else:
                yield chunk

        if pushed:
            sourcepath_stack.pop(-1)

    return _walk


def walk_finalize_streamfragment(chunk):
    return chunk if isinstance(
        chunk, StreamFragment) else textchunk_to_streamfragment(chunk)


def walk(
        dispatcher, node, definition=None,
        walk_decorator=walk_stacktracking_streamfragment,
        finalize_chunk=walk_finalize_streamfragment):
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

    Advanced optional arguments:

    walk_decorator
        The decorator function that will be applied to the inner walk
        function.  By default the walk_stacktracking_streamfragment
        function will be passed in, so that the source will be filled
        from the sourcepath attribute of the node or the most immediate
        parent that have declared one.  Otherwise, an identity function
        can be passed in to disable this.

    finalize_chunk
        The function that will turn chunks into their finalized form.
        This defaults to walk_finalize_streamfragment, so the remainder
        TextChunks will be converted into StreamFragments.

    While the dispatcher object is able to provide the lookup directly,
    this extra definition argument allow more flexibility in having
    Token subtypes being able to provide specific definitions also that
    may be required, such as the generation of optional rendering
    output.
    """

    # The inner walk function - this is actually exposed to the token
    # rule objects so they can also make use of it to process the node
    # with the dispatcher.

    @walk_decorator
    def _walk(dispatcher, node, definition=None):

        if definition is None:
            definition = dispatcher[node]

        if not isinstance(definition, Iterable):
            if definition is dispatcher[node]:
                raise TypeError(
                    "definition for '%s' is not an iterable" % (
                        node.__class__.__name__))
            else:
                raise TypeError(
                    "custom definition %r provided with '%r' is not an "
                    "iterable" % (node.__class__.__name__, node))

        for rule in definition:
            if isinstance(rule, Token):
                # tokens are callables that will generate the chunks
                # that will ultimately form the output, so simply invoke
                # that with this function, the dispatcher and the node.
                for chunk in rule(_walk, dispatcher, node):
                    yield chunk
                continue
            elif isinstance(rule, type):
                for chunk in dispatcher.layout_chunk(rule, node):
                    yield chunk
                continue

            raise TypeError(
                '%r is not a supported Rule subclass or instance; '
                'the cause was node %r and definition %r ' % (
                    rule, node, definition,
                )
            )

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

        # The contracted layout rule chunks to be formed.
        normalized_lrcs = []
        # the preliminary stack that will be cleared whenever a
        # normalized layout rule chunk is generated.
        lrcs_stack = []
        rule_stack = []

        # first pass: generate both the normalized/finalized lrcs.
        for lrc in layout_rule_chunks:
            rule_stack.append(lrc.rule)
            handler = dispatcher(tuple(rule_stack))
            if handler is NotImplemented:
                # not implemented so we keep going; also add the chunk
                # to the stack.
                lrcs_stack.append(lrc)
                continue
            # so a handler is found, generate a new layout rule chunk,
            # and junk the stack.
            normalized_lrcs.append(LayoutChunk(
                tuple(rule_stack), handler, layout_rule_chunks[0].node))
            lrcs_stack[:] = []
            rule_stack[:] = []

        # second pass: now the processing can be done.
        for lr_chunk in chain(normalized_lrcs, lrcs_stack):
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
        yield finalize_chunk(chunk)
