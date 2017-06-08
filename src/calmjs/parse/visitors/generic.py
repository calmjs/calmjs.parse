###############################################################################
#
# Copyright (c) 2011 Ruslan Spivak
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

__author__ = 'Ruslan Spivak <ruslan.spivak@gmail.com>'

from calmjs.parse.asttypes import Node


class ASTVisitor(object):
    """Base class for custom AST node visitors.

    Example:

    >>> from calmjs.parse.parsers.es5 import Parser
    >>> from calmjs.parse.visitors.generic import ASTVisitor
    >>>
    >>> text = '''
    ... var x = {
    ...     "key1": "value1",
    ...     "key2": "value2"
    ... };
    ... '''
    >>>
    >>> class MyVisitor(ASTVisitor):
    ...     def visit_Object(self, node):
    ...         '''Visit object literal.'''
    ...         for prop in node:
    ...             left, right = prop.left, prop.right
    ...             print('Property value: %s' % right.value)
    ...             # visit all children in turn
    ...             self.visit(prop)
    ...
    >>>
    >>> parser = Parser()
    >>> tree = parser.parse(text)
    >>> visitor = MyVisitor()
    >>> visitor.visit(tree)
    Property value: "value1"
    Property value: "value2"

    """

    def visit(self, node):
        method = 'visit_%s' % node.__class__.__name__
        return getattr(self, method, self.generic_visit)(node)

    def generic_visit(self, node):
        for child in node:
            self.visit(child)


class NodeVisitor(object):
    """Simple node visitor."""

    def visit(self, node):
        """Returns a generator that walks all children recursively."""
        for child in node:
            yield child
            for subchild in self.visit(child):
                yield subchild


class ConditionalVisitor(object):
    """
    A visitor that return only specific nodes that matches a condition.
    The condition is specified as a function that accept a single Node
    as the argument, which the function may use to evaluate and return
    True if the node is to be yielded.

    Example usage:

    >>> from calmjs.parse.asttypes import Assign
    >>> from calmjs.parse.asttypes import FunctionCall
    >>> from calmjs.parse.parsers.es5 import Parser
    >>> from calmjs.parse.visitors.generic import ConditionalVisitor
    >>> from calmjs.parse.visitors.es5 import PrettyPrinter as ECMAVisitor
    >>>
    >>> text = '''
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
    >>> visitor = ConditionalVisitor()
    >>> len(list(visitor.generate(tree, assignment)))
    2
    >>> len(list(visitor.generate(tree, function_call)))
    0
    >>> print(ECMAVisitor().visit(visitor.extract(tree, assignment)))
    globals[k] = v
    >>> print(ECMAVisitor().visit(visitor.extract(tree, assignment, skip=1)))
    globals[k] = 'yyy'
    >>> visitor.extract(tree, function_call)
    Traceback (most recent call last):
    ...
    TypeError: no match found
    """

    def generate(self, node, condition):
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
            for subchild in self.generate(child, condition):
                yield subchild

    def extract(self, node, condition, skip=0):
        """
        Extract a single node that matches the provided condition,
        otherwise a TypeError is raised.  An optional skip parameter can
        be provided to specify how many matching nodes are to be skipped
        over.
        """

        for child in self.generate(node, condition):
            if not skip:
                return child
            skip -= 1
        raise TypeError('no match found')


class ReprVisitor(object):
    """
    Visitor for the generation of an expanded repr-like form
    recursively down all children.  Useful for showing the exact values
    stored within the parsed AST along under the relevant attribute.
    Any uncollected children (i.e. unbounded to any attribute of a given
    Node) will be listed under the `?children` output attribute.

    Example usage:

    >>> from calmjs.parse.parsers.es5 import Parser
    >>> from calmjs.parse.visitors.generic import ReprVisitor
    >>> parser = Parser()
    >>> visitor = ReprVisitor()
    >>> tree = parser.parse('var x = function(x, y) { return x + y; };')
    >>> print(visitor.visit(tree))
    <ES5Program ?children=[<VarStatement ?children=[...]>]>

    """

    def visit(
            self, node, omit=('lexpos', 'lineno'), indent=0, depth=-1,
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
                attrs.append((k, self.visit(
                    v, omit, indent, depth - 1, _level)))
            elif isinstance(v, list):
                items = []
                for i in v:
                    if id(i) in ids:
                        ids.remove(id(i))
                    items.append(self.visit(
                        i, omit, indent, depth - 1, _level + 1))
                attrs.append(
                    (k, '[' + header + joiner.join(items) + tailer + ']'))
            else:
                attrs.append((k, v.__repr__()))

        if ids:
            # for unnamed child nodes.
            attrs.append(('?children', '[' + header + joiner.join(
                self.visit(child, omit, indent, depth - 1, _level + 1)
                for child in children
                if id(child) in ids) + tailer + ']'))

        omit_keys = () if not omit else set(omit)
        return '<%s %s>' % (node.__class__.__name__, ', '.join(
            '%s=%s' % (k, v) for k, v in sorted(attrs)
            if k not in omit_keys
        ))

    def __call__(self, node, indent=2, depth=3):
        return self.visit(node, indent=indent, depth=depth)


def visit(node):
    visitor = NodeVisitor()
    for child in visitor.visit(node):
        yield child
