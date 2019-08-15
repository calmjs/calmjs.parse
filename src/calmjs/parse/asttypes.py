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

from __future__ import unicode_literals

__author__ = 'Ruslan Spivak <ruslan.spivak@gmail.com>'

from collections import defaultdict
from ply.lex import LexToken
from calmjs.parse.utils import str
from calmjs.parse.utils import repr_compat

# This should be nodetypes; asttypes means type of AST, and defining a
# type for the entire tree is not the scope of what's being defined here


class Node(object):
    lexpos = lineno = colno = None
    sourcepath = None
    comments = None

    def __init__(self, children=None):
        self._children_list = [] if children is None else children
        self._token_map = {}

    def getpos(self, s, idx):
        token_map = getattr(self, '_token_map', NotImplemented)
        if token_map is NotImplemented:
            return (None, None, None)

        token_list = token_map.get(s, [])
        if idx < len(token_list):
            return token_list[idx]
        else:
            return (0, 0, 0)

    def findpos(self, p, idx):
        lexpos = p.lexpos(idx)
        lineno = p.lineno(idx)
        # YaccProduction does not provide helpers for colno, so query
        # for a helper out of class and see if it helps...
        colno = (
            p.lexer.lookup_colno(lineno, lexpos)
            if lineno > 0 and callable(getattr(p.lexer, 'lookup_colno', None))
            else 0)
        return lexpos, lineno, colno

    def setpos(self, p, idx=1, additional=()):
        """
        This takes a production produced by the lexer and set various
        attributes for this node, such as the positions in the original
        source that defined this token, along with other "hidden" tokens
        that should be converted into comment nodes associated with this
        node.
        """

        self._token_map = defaultdict(list)

        # only do so if the lexer has comments enabled, and that the
        # production at the index actually has a token provided (which
        # presumes that this is the lowest level node being produced).
        if p.lexer.with_comments and isinstance(p.slice[idx], LexToken):
            self.set_comments(p, idx)

        self.lexpos, self.lineno, self.colno = self.findpos(p, idx)
        for i, token in enumerate(p):
            if not isinstance(token, str):
                continue
            self._token_map[token].append(self.findpos(p, i))

        for token, i in additional:
            self._token_map[token].append(self.findpos(p, i))

        # the very ugly debugger invocation for locating the special
        # cases that are required

        # if not self.lexpos and not self.lineno:
        #     print('setpos', self.__class__.__name__, p.stack,
        #           self.lexpos, self.lineno, self.colno)
        #     # uncomment when yacc_tracking is True
        #     # import pdb;pdb.set_trace()
        #     # uncomment when yacc_tracking is False
        #     # import sys
        #     # from traceback import extract_stack
        #     # _src = extract_stack(sys._getframe(1), 1)[0].line
        #     # if '# require yacc_tracking' not in _src:
        #     #     import pdb;pdb.set_trace()

    def set_comments(self, p, idx):
        """
        Set comments associated with the element inside the production
        rule provided referenced by idx to this node.  Only applicable
        if the element is a LexToken and that the hidden_tokens is set.
        """

        comments = []
        # reversing the order to capture the first pos in the
        # laziest way possible.
        for token in reversed(getattr(p.slice[idx], 'hidden_tokens', [])):
            if token.type == 'LINE_COMMENT':
                comment = LineComment(token.value)
            elif token.type == 'BLOCK_COMMENT':
                comment = BlockComment(token.value)
            else:
                continue  # pragma: no cover

            # short-circuit the setpos only
            pos = (token.lexpos, token.lineno, token.colno)
            comment.lexpos, comment.lineno, comment.colno = pos
            comment._token_map = {token.value: [pos]}
            comments.append(comment)

        if comments:
            self.comments = Comments(list(reversed(comments)))
            (self.comments.lexpos, self.comments.lineno,
                self.comments.colno) = pos

    def __iter__(self):
        for child in self.children():
            if child is not None:
                yield child

    # TODO generalize this so subclasses don't need to have their own
    # implementations.  Example: declare a list of attributes to return
    # as children.

    def children(self):
        return getattr(self, '_children_list', [])


class Program(Node):
    pass


class ES5Program(Program):
    pass


class Block(Node):
    pass


class Boolean(Node):
    def __init__(self, value):
        self.value = value


class Null(Node):
    def __init__(self, value):
        assert value == 'null'
        self.value = value


class Number(Node):
    def __init__(self, value):
        self.value = value


class Identifier(Node):
    def __init__(self, value):
        self.value = value


class PropIdentifier(Identifier):
    """
    Technically still an Identifier, but this is to be used for context
    of dealing with properties, where the Identifiers are used as
    a PropertyName in the Object Initialiser (11.1.5), or they are used
    as Property Accessors (11.2.1).
    """


class String(Node):
    def __init__(self, value):
        self.value = value


class Regex(Node):
    def __init__(self, value):
        self.value = value


class Array(Node):
    def __init__(self, items):
        self.items = items

    def children(self):
        return self.items


class List(Node):
    # in JavaScript, this is distinctive from Array.
    def __init__(self, items):
        self.items = items

    def children(self):
        return self.items


class Arguments(List):
    pass


class Object(Node):
    def __init__(self, properties=None):
        self.properties = [] if properties is None else properties

    def children(self):
        return self.properties


class NewExpr(Node):
    def __init__(self, identifier, args=None):
        self.identifier = identifier
        self.args = args

    def children(self):
        return [self.identifier, self.args]


class FunctionCall(Node):
    def __init__(self, identifier, args=None):
        self.identifier = identifier
        self.args = args

    def children(self):
        return [self.identifier, self.args]


class BracketAccessor(Node):
    def __init__(self, node, expr):
        self.node = node
        self.expr = expr

    def children(self):
        return [self.node, self.expr]


class DotAccessor(Node):
    def __init__(self, node, identifier):
        self.node = node
        self.identifier = identifier

    def children(self):
        return [self.node, self.identifier]


class Assign(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def children(self):
        return [self.left, self.right]


class GetPropAssign(Node):
    def __init__(self, prop_name, elements):
        """elements - function body"""
        self.prop_name = prop_name
        self.elements = elements or []

    def children(self):
        return [self.prop_name] + self.elements


class SetPropAssign(Node):
    def __init__(self, prop_name, parameter, elements):
        """elements - function body"""
        self.prop_name = prop_name
        self.parameter = parameter
        self.elements = elements or []

    def children(self):
        return [self.prop_name, self.parameter] + self.elements


class VarStatement(Node):
    pass


class VarDecl(Node):
    def __init__(self, identifier, initializer=None):
        self.identifier = identifier
        self.initializer = initializer

    def children(self):
        return [self.identifier, self.initializer]


class VarDeclNoIn(VarDecl):
    """
    Specialized for the ForIn Node.
    """


class UnaryExpr(Node):
    def __init__(self, op, value, postfix=False):
        self.op = op
        self.value = value

    def children(self):
        return [self.value]


class PostfixExpr(UnaryExpr):
    def __init__(self, op, value):
        self.op = op
        self.value = value


class BinOp(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def children(self):
        return [self.left, self.right]


class GroupingOp(Node):
    def __init__(self, expr):
        self.expr = expr

    def children(self):
        return [self.expr]


class Conditional(Node):
    """Conditional Operator ( ? : )"""
    def __init__(self, predicate, consequent, alternative):
        self.predicate = predicate
        self.consequent = consequent
        self.alternative = alternative

    def children(self):
        return [self.predicate, self.consequent, self.alternative]


class If(Node):
    def __init__(self, predicate, consequent, alternative=None):
        self.predicate = predicate
        self.consequent = consequent
        self.alternative = alternative

    def children(self):
        return [self.predicate, self.consequent, self.alternative]


class DoWhile(Node):
    def __init__(self, predicate, statement):
        self.predicate = predicate
        self.statement = statement

    def children(self):
        return [self.predicate, self.statement]


class While(Node):
    def __init__(self, predicate, statement):
        self.predicate = predicate
        self.statement = statement

    def children(self):
        return [self.predicate, self.statement]


class For(Node):
    def __init__(self, init, cond, count, statement):
        self.init = init
        self.cond = cond
        self.count = count
        self.statement = statement

    def children(self):
        return [self.init, self.cond, self.count, self.statement]


class ForIn(Node):
    def __init__(self, item, iterable, statement):
        self.item = item
        self.iterable = iterable
        self.statement = statement

    def children(self):
        return [self.item, self.iterable, self.statement]


class Continue(Node):
    def __init__(self, identifier=None):
        self.identifier = identifier

    def children(self):
        return [self.identifier]


class Break(Node):
    def __init__(self, identifier=None):
        self.identifier = identifier

    def children(self):
        return [self.identifier]


class Return(Node):
    def __init__(self, expr=None):
        self.expr = expr

    def children(self):
        return [self.expr]


class With(Node):
    def __init__(self, expr, statement):
        self.expr = expr
        self.statement = statement

    def children(self):
        return [self.expr, self.statement]


class Switch(Node):

    def __init__(self, expr, case_block):
        self.expr = expr
        self.case_block = case_block

    def children(self):
        return [self.expr, self.case_block]


class CaseBlock(Block):
    pass


class Case(Node):
    def __init__(self, expr, elements):
        self.expr = expr
        self.elements = elements if elements is not None else []

    def children(self):
        return [self.expr] + self.elements


class Default(Node):
    def __init__(self, elements):
        self.elements = elements if elements is not None else []

    def children(self):
        return self.elements


class Label(Node):
    def __init__(self, identifier, statement):
        self.identifier = identifier
        self.statement = statement

    def children(self):
        return [self.identifier, self.statement]


class Throw(Node):
    def __init__(self, expr):
        self.expr = expr

    def children(self):
        return [self.expr]


class Try(Node):
    def __init__(self, statements, catch=None, fin=None):
        self.statements = statements
        self.catch = catch
        self.fin = fin

    def children(self):
        return [self.statements] + [self.catch, self.fin]


class Catch(Node):
    def __init__(self, identifier, elements):
        self.identifier = identifier
        self.elements = elements

    def children(self):
        return [self.identifier, self.elements]


class Finally(Node):
    def __init__(self, elements):
        self.elements = elements

    def children(self):
        return [self.elements]


class Debugger(Node):
    def __init__(self, value):
        self.value = value


class FuncBase(Node):
    def __init__(self, identifier, parameters, elements):
        self.identifier = identifier
        self.parameters = parameters if parameters is not None else []
        self.elements = elements if elements is not None else []

    def children(self):
        return [self.identifier] + self.parameters + self.elements


class FuncDecl(FuncBase):
    pass


# The only difference is that function expression might not have an identifier
class FuncExpr(FuncBase):
    pass


class Comma(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def children(self):
        return [self.left, self.right]


class EmptyStatement(Node):
    def __init__(self, value):
        self.value = value


class ExprStatement(Node):
    def __init__(self, expr):
        self.expr = expr

    def children(self):
        return [self.expr]


class Elision(Node):
    def __init__(self, value):
        self.value = value


class This(Node):
    def __init__(self):
        pass


# Currently, as the comment nodes are typically instantiated directly by
# the Node.setpos method defined by the class in this module, and that
# there isn't a easy way to reference the factory produced subclasses
# that has the appropriate language specific __str__ or __repr__ defined
# for them, they will be defined as such.


class Comments(Node):

    def __str__(self):
        return str('\n').join(str(child) for child in self.children())

    def __repr__(self):
        return str('<%s ?children=[%s]>' % (
            type(self).__name__,
            str(', ').join(repr(child) for child in self.children()),
        ))


class Comment(Node):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return str('<%s value=%s>' % (
            type(self).__name__, repr_compat(self.value)))


class BlockComment(Comment):
    pass


class LineComment(Comment):
    pass
