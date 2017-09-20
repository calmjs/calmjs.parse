# -*- coding: utf-8 -*-
"""
Classes for achieving the name mangling effect.
"""

from __future__ import unicode_literals

import logging
from operator import itemgetter
from itertools import count
from itertools import product

from calmjs.parse.ruletypes import PushScope
from calmjs.parse.ruletypes import PopScope
from calmjs.parse.ruletypes import PushCatch
from calmjs.parse.ruletypes import PopCatch
from calmjs.parse.ruletypes import Declare
from calmjs.parse.ruletypes import Resolve
from calmjs.parse.ruletypes import ResolveFuncName

from calmjs.parse.unparsers.walker import Dispatcher
from calmjs.parse.unparsers.walker import walk

from calmjs.parse.handlers.core import token_handler_unobfuscate

logger = logging.getLogger(__name__)
logger.level = logging.WARNING

ID_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'


class NameGenerator(object):
    """
    A name generator.  It can accept one argument for values that should
    be skipped.

    It is also a constructor so that further names can be skipped.
    """

    def __init__(self, skip=None, charset=ID_CHARS):
        self.skip = set(skip or [])
        self.charset = charset
        self.__iterself = iter(self)

    def __call__(self, skip):
        return type(self)(set(skip) | set(self.skip), self.charset)

    def __iter__(self):
        for n in count(1):
            for chars in product(self.charset, repeat=n):
                symbol = ''.join(chars)
                if symbol in self.skip:
                    continue
                yield symbol

    def __next__(self):
        return next(self.__iterself)

    # python2.7 compatibility.
    next = __next__


# TODO provide an option to memoize all properties to reduce computation
# TODO generic Scope class for the common code (for tracking execution
# context also?)

class Scope(object):
    """
    For tracking the symbols.
    """

    def __init__(self, node, parent=None):
        self._closed = False
        self.node = node
        self.parent = parent
        self.children = []

        # Local names is for this scope only, the variable name will be
        # the key, with a value of how many times it has been referenced
        # anywhere in this scope.
        self.referenced_symbols = {}

        # This is a set of names that have been declared (i.e. via var
        # or function)
        self.local_declared_symbols = set()

        # All symbols remapped to be remapped to a different name will
        # be stored here, for the resolved method to make use of.
        self.remapped_symbols = {}

    @property
    def declared_symbols(self):
        """
        Return all local symbols here, and also of the parents
        """

        return self.local_declared_symbols | (
            self.parent.declared_symbols if self.parent else set())

    @property
    def global_symbols(self):
        """
        These are symbols that have been referenced, but not declared
        within this scope or any parent scopes.
        """

        declared_symbols = self.declared_symbols
        return set(
            s for s in self.referenced_symbols if s not in declared_symbols)

    @property
    def global_symbols_in_children(self):
        """
        This is based on all children referenced symbols that have not
        been declared.

        The intended use case is to ban the symbols from being used as
        remapped symbol values.
        """

        result = set()
        for child in self.children:
            result |= (
                child.global_symbols |
                child.global_symbols_in_children)
        return result

    @property
    def non_local_symbols(self):
        """
        Non local symbols are all referenced symbols that are not
        locally declared here.
        """

        return set(self.referenced_symbols) - self.local_declared_symbols

    @property
    def leaked_referenced_symbols(self):
        return {
            k: v for k, v in self.referenced_symbols.items()
            if k not in self.local_declared_symbols
        }

    def declare(self, symbol):
        self.local_declared_symbols.add(symbol)
        # simply create the reference, if not already there.
        self.referenced_symbols[symbol] = self.referenced_symbols.get(
            symbol, 0)

    def reference(self, symbol, count=1):
        # increment reference counter, declare one if not already did.
        self.referenced_symbols[symbol] = self.referenced_symbols.get(
            symbol, 0) + count

    def close(self):
        """
        Mark the scope as closed, i.e. all symbols have been declared,
        and no further declarations should be done.
        """

        if self._closed:
            raise ValueError('scope is already marked as closed')

        # By letting parent know which symbols this scope has leaked, it
        # will let them reserve all lowest identifiers first.
        if self.parent:
            for symbol, c in self.leaked_referenced_symbols.items():
                self.parent.reference(symbol, c)

        self._closed = True

    def close_all(self):
        """
        Recursively close everything.
        """

        for child in self.children:
            child.close_all()
        self.close()

    @property
    def _reserved_symbols(self):
        """
        Helper property for the build_remap_symbols method.  This
        property first resolves _all_ local references from parents,
        skipping all locally declared symbols as the goal is to generate
        a local mapping for them, but in a way not to shadow over any
        already declared symbols from parents, and also the implicit
        globals in all children.

        This is marked "private" as there are a number of computations
        involved, and is really meant for the build_remap_symbols to use
        for its standard flow.
        """

        # In practice, and as a possible optimisation, the parent's
        # remapped symbols table can be merged into this instance, but
        # this bloats memory use and cause unspecified reservations that
        # may not be applicable this or any child scope.  So for clarity
        # and purity of references made, this somewhat more involved way
        # is done instead.
        remapped_parents_symbols = {
            self.resolve(v) for v in self.non_local_symbols}

        return (
            # block implicit children globals.
            self.global_symbols_in_children |
            # also not any global symbols
            self.global_symbols |
            # also all remapped parent symbols referenced here
            remapped_parents_symbols
        )

    def build_remap_symbols(self, name_generator, children_only=True):
        """
        This builds the replacement table for all the defined symbols
        for all the children, and this scope, if the children_only
        argument is False.
        """

        if not children_only:
            replacement = name_generator(skip=(self._reserved_symbols))
            for symbol, c in reversed(sorted(
                    self.referenced_symbols.items(), key=itemgetter(1, 0))):
                if symbol not in self.local_declared_symbols:
                    continue
                self.remapped_symbols[symbol] = next(replacement)

        for child in self.children:
            child.build_remap_symbols(name_generator, False)

    def resolve(self, symbol):
        result = None
        scope = self
        while result is None and scope:
            result = scope.remapped_symbols.get(symbol)
            scope = scope.parent
        return result or symbol

    def nest(self, node, cls=None):
        """
        Create a new nested scope that is within this instance, binding
        the provided node to it.
        """

        if cls is None:
            cls = type(self)

        nested_scope = cls(node, self)
        self.children.append(nested_scope)
        return nested_scope

    def funcdecl(self, node):
        return self.nest(node, Scope)

    def catchctx(self, node):
        return self.nest(node, CatchScope)


class CatchScope(Scope):
    """
    Special scope for dealing with catch only.  It ends up proxying a
    whole bunch of calls to the actual scope which is the parent.
    """

    def __init__(self, node, parent):
        """
        Parent is required, the symbol _is_ the symbol that the catch
        statement was referenced.
        """

        if not isinstance(parent, Scope):
            raise TypeError('CatchScopes must have a Scope as a parent')
        self.node = node
        self.parent = parent
        self.children = []
        self.catch_symbol = node.identifier.value
        self.catch_symbol_usage = 0
        self.remapped_symbols = {}
        self._closed = False

    @property
    def referenced_symbols(self):
        # generate a new table with the immediate parent scope, plus the
        # count of the catch symbol used.
        # TODO when close is called, return a frozen value (memoize).
        result = {self.catch_symbol: self.catch_symbol_usage}
        result.update(self.parent.referenced_symbols)
        return result

    @property
    def local_declared_symbols(self):
        # like above, only provide symbols used locally here.
        return self.parent.local_declared_symbols | {self.catch_symbol}

    @property
    def declared_symbols(self):
        """
        Return all local symbols here, and also of the parents
        """

        return {self.catch_symbol} | self.parent.declared_symbols

    @property
    def non_local_symbols(self):
        """
        For the catch scope, in order for the reserved symbols check to
        work for all cases, only remove the catch_symbol.
        """

        return set(self.referenced_symbols) - {self.catch_symbol}

    def declare(self, symbol):
        """
        Nothing gets declared here - it's the parents problem, except
        for the case where the symbol is the one we have here.
        """

        if symbol != self.catch_symbol:
            self.parent.declare(symbol)

    def reference(self, symbol, count=1):
        """
        However, if referenced, ensure that the counter is applied to
        the catch symbol.
        """

        if symbol == self.catch_symbol:
            self.catch_symbol_usage += count
        else:
            self.parent.reference(symbol, count)

    def close(self):
        """
        Since all child close calls will reference this, which in turn
        reference parent with the count, nothing needs to be done
        otherwise the parent reference count will be doubled for no
        reason.
        """

        if self._closed:
            raise ValueError('scope is already marked as closed')

        self._closed = True

    def build_remap_symbols(self, name_generator, children_only=None):
        """
        The children_only flag is inapplicable, but this is included as
        the Scope class is defined like so.

        Here this simply just place the catch symbol with the next
        replacement available.
        """

        replacement = name_generator(skip=(self._reserved_symbols))
        self.remapped_symbols[self.catch_symbol] = next(replacement)

        # also to continue down the children.
        for child in self.children:
            child.build_remap_symbols(name_generator, False)


class Obfuscator(object):
    """
    The name obfuscator.
    """

    def __init__(
            self,
            obfuscate_globals=False,
            shadow_funcname=False,
            reserved_keywords=()):
        """
        Arguments

        obfuscate_globals
            Also obfuscate variables declared on the global scope.  Do
            not enable this option unless there is an explicit need to
            do so as this will likely result in code that no longer
            provide the global variable names at where they were
            expected.

            Defaults to False for the reason above.

        shadow_funcname
            If True, obfuscated names within a function can shadow the
            function name that it was defined for.  In strict mode for
            Safari, names within a function cannot shadow over the name
            that the function was declared as.

            Defaults to False.

        reserved_keywords
            A list of reserved keywords for the input AST that should
            not be used as an obfuscated identifier.  Defaults to an
            empty tuple.
        """

        # this is a mapping of Identifier nodes to the scope
        self.identifiers = {}
        self.scopes = {}
        self.stack = []
        self.obfuscate_globals = obfuscate_globals
        self.shadow_funcname = shadow_funcname
        self.reserved_keywords = reserved_keywords
        # global scope is in the ether somewhere so it isn't exactly
        # bounded to any specific node that gets passed in.
        self.global_scope = Scope(None)
        self.stack.append(self.global_scope)

    @property
    def current_scope(self):
        return self.stack[-1]

    def push_scope(self, dispatcher, node, *a, **kw):
        scope = self.current_scope.funcdecl(node)
        self.scopes[node] = scope
        self.stack.append(scope)

    def push_catch(self, dispatcher, node, *a, **kw):
        scope = self.current_scope.catchctx(node)
        self.scopes[node] = scope
        self.stack.append(scope)

    def pop_scope(self, dispatcher, node, *a, **kw):
        scope = self.stack.pop()
        scope.close()
        # TODO figure out whether/how to check that the scope that just
        # got popped is indeed of this node.

    def declare(self, dispatcher, node):
        """
        Declare the value of the Identifier of the node that was passed
        in as used in the current scope.
        """

        self.current_scope.declare(node.value)

    def register_reference(self, dispatcher, node):
        """
        Register this identifier to the current scope, and mark it as
        referenced in the current scope.
        """

        # the identifier node itself will be mapped to the current scope
        # for the resolve to work
        # This should probably WARN about the node object being already
        # assigned to an existing scope that isn't current_scope.
        self.identifiers[node] = self.current_scope
        self.current_scope.reference(node.value)

    def shadow_reference(self, dispatcher, node):
        """
        Only simply make a reference to the value in the current scope,
        specifically for the FuncBase type.
        """

        # as opposed to the previous one, only add the value of the
        # identifier itself to the scope so that it becomes reserved.
        self.current_scope.reference(node.identifier.value)

    def resolve(self, dispatcher, node):
        """
        For the given node, resolve it into the scope it was declared
        at, and if one was found, return its value.
        """

        scope = self.identifiers.get(node)
        if not scope:
            return node.value
        return scope.resolve(node.value)

    def walk(self, dispatcher, node):
        """
        Walk through the node with a custom dispatcher for extraction of
        details that are required.
        """

        deferrable_handlers = {
            Declare: self.declare,
            Resolve: self.register_reference,
        }
        layout_handlers = {
            PushScope: self.push_scope,
            PopScope: self.pop_scope,
            PushCatch: self.push_catch,
            # should really be different, but given that the
            # mechanism is within the same tree, the only difference
            # would be sanity check which should have been tested in
            # the first place in the primitives anyway.
            PopCatch: self.pop_scope,
        }

        if not self.shadow_funcname:
            layout_handlers[ResolveFuncName] = self.shadow_reference

        local_dispatcher = Dispatcher(
            definitions=dict(dispatcher),
            token_handler=None,
            layout_handlers=layout_handlers,
            deferrable_handlers=deferrable_handlers,
        )
        return list(walk(local_dispatcher, node))

    def finalize(self):
        """
        Finalize the run - build the name generator and use it to build
        the remap symbol tables.
        """

        self.global_scope.close()
        name_generator = NameGenerator(skip=self.reserved_keywords)
        self.global_scope.build_remap_symbols(
            name_generator,
            children_only=not self.obfuscate_globals,
        )

    def prewalk_hook(self, dispatcher, node):
        """
        This is for the Unparser to use as a prewalk hook.
        """

        self.walk(dispatcher, node)
        self.finalize()
        return node


def obfuscate(
        obfuscate_globals=False, shadow_funcname=False, reserved_keywords=()):
    """
    An example, barebone name obfuscation ruleset

    obfuscate_globals
        If true, identifier names on the global scope will also be
        obfuscated.  Default is False.
    shadow_funcname
        If True, obfuscated function names will be shadowed.  Default is
        False.
    reserved_keywords
        A tuple of strings that should not be generated as obfuscated
        identifiers.
    """

    def name_obfuscation_rules():
        inst = Obfuscator(
            obfuscate_globals=obfuscate_globals,
            shadow_funcname=shadow_funcname,
            reserved_keywords=reserved_keywords,
        )
        return {
            'token_handler': token_handler_unobfuscate,
            'deferrable_handlers': {
                Resolve: inst.resolve,
            },
            'prewalk_hooks': [
                inst.prewalk_hook,
            ],
        }
    return name_obfuscation_rules
