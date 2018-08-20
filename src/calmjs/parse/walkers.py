# -*- coding: utf-8 -*-
"""
Generic walkers.
"""

from __future__ import unicode_literals

from calmjs.parse.asttypes import Node
from calmjs.parse.utils import repr_compat


class Walker(object):
    """
    The generic walker that will walk through the asttypes tree.

    It also provide a couple helper methods that serves as filters, i.e.
    it will only return specific nodes that match the conditions that
    were provided.

    The condition is specified as a function that accept a single Node
    as the argument, which the function may use to evaluate and return
    True if the node is to be yielded.

    Example usage:

    >>> from calmjs.parse.asttypes import Assign
    >>> from calmjs.parse.asttypes import FunctionCall
    >>> from calmjs.parse.parsers.es5 import Parser
    >>> from calmjs.parse.unparsers.es5 import pretty_print
    >>> from calmjs.parse.walkers import Walker
    >>>
    >>> text = u'''
    ... var globals = {};
    ... function x(k, v) {
    ...     globals[k] = v;
    ... };
    ...
    ... function y(k) {
    ...     globals[k] = 'yyy';
    ... };
    ... '''
    >>> def assignment(node):
    ...     return isinstance(node, Assign)
    ...
    >>> def function_call(node):
    ...     return isinstance(node, FunctionCall)
    ...
    >>> tree = Parser().parse(text)
    >>> walker = Walker()
    >>> len(list(walker.filter(tree, assignment)))
    2
    >>> len(list(walker.filter(tree, function_call)))
    0
    >>> print(pretty_print(walker.extract(tree, assignment)))
    globals[k] = v
    >>> print(pretty_print(walker.extract(tree, assignment, skip=1)))
    globals[k] = 'yyy'
    >>> walker.extract(tree, function_call)
    Traceback (most recent call last):
    ...
    TypeError: no match found
    """

    def walk(self, node, condition=None):
        """
        Simply walk through the entire node; condition argument is
        ignored.
        """

        if not isinstance(node, Node):
            raise TypeError('not a node')

        for child in node:
            yield child
            for subchild in self.walk(child, condition):
                yield subchild

    def filter(self, node, condition):
        """
        This method accepts a node and the condition function; a
        generator will be returned to yield the nodes that got matched
        by the condition.
        """

        if not isinstance(node, Node):
            raise TypeError('not a node')

        for child in node:
            if condition(child):
                yield child
            for subchild in self.filter(child, condition):
                yield subchild

    def extract(self, node, condition, skip=0):
        """
        Extract a single node that matches the provided condition,
        otherwise a TypeError is raised.  An optional skip parameter can
        be provided to specify how many matching nodes are to be skipped
        over.
        """

        for child in self.filter(node, condition):
            if not skip:
                return child
            skip -= 1
        raise TypeError('no match found')


class ReprWalker(object):
    """
    Walker for the generation of an expanded repr-like form recursively
    down all children of an asttypes Node.  Useful for showing the exact
    values stored within the tree along under the relevant attribute.
    Any uncollected children (i.e. unbounded to any attribute of a given
    Node) will be listed under the `?children` output attribute.

    Example usage:

    >>> from calmjs.parse.parsers.es5 import Parser
    >>> from calmjs.parse.walkers import ReprWalker
    >>> parser = Parser()
    >>> repr_walker = ReprWalker()
    >>> tree = parser.parse(u'var x = function(x, y) { return x + y; };')
    >>> print(repr_walker.walk(tree))
    <ES5Program ?children=[<VarStatement ?children=[...]>]>

    Standard call is the repr mode - if stable output is desired across
    major semantic versions, always use the walk method.

    >>> print(repr_walker(tree))
    <ES5Program @1:1 ?children=[
      <VarStatement @1:1 ?children=[...]>
    ]>

    """

    def walk(
            self, node, omit=(
                'lexpos', 'lineno', 'colno', 'rowno'),
            indent=0, depth=-1,
            pos=False,
            _level=0):
        """
        Accepts the standard node argument, along with an optional omit
        flag - it should be an iterable that lists out all attributes
        that should be omitted from the repr output.
        """

        if not depth:
            return '<%s ...>' % node.__class__.__name__

        attrs = []
        children = node.children()
        ids = {id(child) for child in children}

        indentation = ' ' * (indent * (_level + 1))
        header = '\n' + indentation if indent else ''
        joiner = ',\n' + indentation if indent else ', '
        tailer = '\n' + ' ' * (indent * _level) if indent else ''

        for k, v in vars(node).items():
            if k.startswith('_'):
                continue
            if id(v) in ids:
                ids.remove(id(v))

            if isinstance(v, Node):
                attrs.append((k, self.walk(
                    v, omit, indent, depth - 1, pos, _level)))
            elif isinstance(v, list):
                items = []
                for i in v:
                    if id(i) in ids:
                        ids.remove(id(i))
                    items.append(self.walk(
                        i, omit, indent, depth - 1, pos, _level + 1))
                attrs.append(
                    (k, '[' + header + joiner.join(items) + tailer + ']'))
            else:
                attrs.append((k, repr_compat(v)))

        if ids:
            # for unnamed child nodes.
            attrs.append(('?children', '[' + header + joiner.join(
                self.walk(child, omit, indent, depth - 1, pos, _level + 1)
                for child in children
                if id(child) in ids) + tailer + ']'))

        position = ('@%s:%s ' % (
            '?' if node.lineno is None else node.lineno,
            '?' if node.colno is None else node.colno,
        ) if pos else '')

        omit_keys = () if not omit else set(omit)
        return '<%s %s%s>' % (node.__class__.__name__, position, ', '.join(
            '%s=%s' % (k, v) for k, v in sorted(attrs)
            if k not in omit_keys
        ))

    def __call__(self, node, indent=2, depth=3, pos=True):
        return self.walk(node, indent=indent, depth=depth, pos=pos)


def walk(node):
    """
    Walk through every node and yield the result
    """

    for n in Walker().walk(node):
        yield n
