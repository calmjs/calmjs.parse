# -*- coding: utf-8 -*-
"""
Provides factories to build classes.
"""

from functools import partial
from calmjs.parse import asttypes


class _M(object):
    pass


class Factory(object):
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
                # type(_M) replicates the removed types.ClassType
                v for v in vars(module).values() if isinstance(v, type(_M))
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


AstTypesFactory = partial(Factory, asttypes)
