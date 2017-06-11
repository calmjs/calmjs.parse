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


class Node(object):
    def __init__(self, children=None):
        self._children_list = [] if children is None else children
        self.lexpos = self.lineno = self.colno = None

    def setpos(self, p, idx=1):
        self.lexpos = p.lexpos(idx)
        self.lineno = p.lineno(idx)
        # YaccProduction does not provide helpers for colno, so query
        # for a helper out of class and see if it helps...
        self.colno = (
            p.lexer.lookup_colno(self.lineno, self.lexpos) if callable(
                getattr(p.lexer, 'lookup_colno', None)) else 0
        )

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

    def __iter__(self):
        for child in self.children():
            if child is not None:
                yield child

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


class Object(Node):
    def __init__(self, properties=None):
        self.properties = [] if properties is None else properties

    def children(self):
        return self.properties


class NewExpr(Node):
    def __init__(self, identifier, args=None):
        self.identifier = identifier
        self.args = [] if args is None else args

    def children(self):
        return [self.identifier, self.args]


class FunctionCall(Node):
    def __init__(self, identifier, args=None):
        self.identifier = identifier
        self.args = [] if args is None else args

    def children(self):
        return [self.identifier] + self.args


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
    def __init__(self, prop_name, parameters, elements):
        """elements - function body"""
        self.prop_name = prop_name
        self.parameters = parameters
        self.elements = elements or []

    def children(self):
        return [self.prop_name] + self.parameters + self.elements


class VarStatement(Node):
    pass


class VarDecl(Node):
    def __init__(self, identifier, initializer=None):
        self.identifier = identifier
        self.initializer = initializer

    def children(self):
        return [self.identifier, self.initializer]


class UnaryOp(Node):
    def __init__(self, op, value, postfix=False):
        self.op = op
        self.value = value
        self.postfix = postfix

    def children(self):
        return [self.value]


class BinOp(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def children(self):
        return [self.left, self.right]


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
    def __init__(self, expr, cases, default=None):
        self.expr = expr
        self.cases = cases
        self.default = default

    def children(self):
        return [self.expr] + self.cases + [self.default]


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
