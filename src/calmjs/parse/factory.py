# -*- coding: utf-8 -*-
"""
Provides factories to build classes.
"""

from importlib import import_module
from functools import partial
from functools import wraps
from calmjs.parse import asttypes

PKGNAME = 'calmjs.parse'  # should derive this.


class SRFactory(object):
    """
    A factory that will generate a new subclass that has the specified
    __str__ and __repr__ implementations.  Given the number of potential
    nodes that a given AST might have, tagging the custom str/repr
    on the class definition itself will only happen once, saving the
    cost of having to allocate all those references per object.
    """

    def __init__(self, module, str_, repr_):
        # recreate the class definitions
        def __str__(self):
            return str_(self)

        def __repr__(self):
            return repr_(self)

        self.module = module
        self.classes = {c.__name__: c for c in (
            type(cls.__name__, (cls,), {
                '__repr__': __repr__,
                '__str__': __str__,
            }) for cls in (
                v for v in vars(module).values() if isinstance(v, type)
            )
        )}

    def __getattr__(self, attr):
        if attr not in self.classes:
            raise AttributeError('%s "%s" has no attribute %r' % (
                type(self.module).__name__,
                self.module.__class__.__name__,
                attr,
            ))

        return self.classes[attr]


AstTypesFactory = partial(SRFactory, asttypes)


def RawParserUnparserFactory(parser_name, parse_callable, *unparse_callables):
    """
    Produces a callable object that also has callable attributes that
    passes its first argument to the parent callable.
    """

    def build_unparse(f):
        @wraps(f)
        def unparse(self, source, *a, **kw):
            node = parse_callable(
                source,
                with_comments=kw.pop('with_comments', False),
            )
            return f(node, *a, **kw)
        # a dumb and lazy docstring replacement
        if f.__doc__:
            unparse.__doc__ = f.__doc__.replace(
                'ast\n        The AST ',
                'source\n        The source ',
            )
        return unparse

    def build_parse(f):
        @wraps(f)
        def parse(self, source, *a, **kw):
            return f(source, *a, **kw)
        parse.__name__ = parser_name
        parse.__qualname__ = parser_name
        return parse

    callables = {f.__name__: build_unparse(f) for f in unparse_callables}
    callables['__call__'] = build_parse(parse_callable)
    callables['__module__'] = PKGNAME
    return type(parser_name, (object,), callables)()


def ParserUnparserFactory(module_name, *unparser_names):
    """
    Produce a new parser/unparser object from the names provided.
    """

    parse_callable = import_module(PKGNAME + '.parsers.' + module_name).parse
    unparser_module = import_module(PKGNAME + '.unparsers.' + module_name)
    return RawParserUnparserFactory(module_name, parse_callable, *[
        getattr(unparser_module, name) for name in unparser_names])
