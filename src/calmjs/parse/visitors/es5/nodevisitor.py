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
    >>> from calmjs.parse.visitors.es5.nodevisitor import ASTVisitor
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


class ReprVisitor(object):
    """
    Visitor for the generation of an expanded repr-like form
    recursively down all children.  Useful for showing the exact values
    stored within the parsed AST along under the relevant attribute.
    Any uncollected children (i.e. unbounded to any attribute of a given
    Node) will be listed under the `?children` output attribute.

    Example usage:

    >>> from calmjs.parse.parsers.es5 import Parser
    >>> from calmjs.parse.visitors.es5.nodevisitor import ReprVisitor
    >>> parser = Parser()
    >>> visitor = ReprVisitor()
    >>> tree = parser.parse('var x = function(x, y) { return x + y; };')
    >>> print(visitor.visit(tree))
    <ES5Program ?children=[<VarStatement ?children=[...]>]>

    """

    def visit(self, node, omit=('lexpos', 'lineno')):
        """
        Accepts the standard node argument, along with an optional omit
        flag - it should be an iterable that lists out all attributes
        that should be omitted from the repr output.
        """

        attrs = []
        children = node.children()
        ids = {id(child) for child in children}

        for k, v in vars(node).items():
            if k.startswith('_'):
                continue
            if id(v) in ids:
                ids.remove(id(v))

            if isinstance(v, Node):
                attrs.append((k, self.visit(v)))
            elif isinstance(v, list):
                items = []
                for i in v:
                    if id(i) in ids:
                        ids.remove(id(i))
                    items.append(self.visit(i))
                attrs.append((k, '[' + ', '.join(items) + ']'))
            else:
                attrs.append((k, v.__repr__()))

        if ids:
            # for unnamed child nodes.
            attrs.append(('?children', '[' + ', '.join(
                self.visit(child) for child in children
                if id(child) in ids) + ']'))

        omit_keys = () if not omit else set(omit)
        return '<%s %s>' % (node.__class__.__name__, ', '.join(
            '%s=%s' % (k, v) for k, v in sorted(attrs)
            if k not in omit_keys
        ))


def visit(node):
    visitor = NodeVisitor()
    for child in visitor.visit(node):
        yield child
