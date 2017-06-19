# -*- coding: utf-8 -*-
"""
ES5 base visitors
"""

from calmjs.parse.asttypes import Node

# goal of the following is to produce a document form of the input
# ast node (docgen?)
# which in turn
# markers


class Layout(object):
    """
    Layout markers
    """


class Space(Layout):
    pass


class OptionalSpace(Layout):
    pass


class Newline(Layout):
    pass


class Indent(Layout):
    pass


class Dedent(Layout):
    pass


space = Space()
optional_space = OptionalSpace()
newline = Newline()
indent = Indent()
dedent = Dedent()


class Token(object):
    def __init__(self, attr=None, value=None, pos=0):
        self.attr = attr
        self.value = value
        self.pos = pos

    def __call__(self, visitor, state, node):
        raise NotImplementedError


class Attr(Token):
    """
    Return the value as specified in the attribute
    """

    def _getattr(self, state, node):
        if callable(self.attr):
            return self.attr(node)
        else:
            return getattr(node, self.attr)

    def visit_subnode(self, visitor, state, node, sub_node):
        if isinstance(sub_node, Node):
            for chunk in visitor.visit(state, sub_node):
                yield chunk
        else:
            for chunk in state(node, sub_node, self):
                yield chunk

    def __call__(self, visitor, state, node):
        for chunk in self.visit_subnode(
                visitor, state, node, self._getattr(state, node)):
            yield chunk


class Text(Token):
    """
    Simple text to add back
    """

    def __call__(self, visitor, state, node):
        for chunk in state(node, self.value, self):
            yield chunk


class JoinAttr(Attr):
    """
    Join the attr with value.
    """

    def __call__(self, visitor, state, node):
        nodes = iter(self._getattr(state, node))

        try:
            target_node = next(nodes)
        except StopIteration:
            return

        for chunk in self.visit_subnode(visitor, state, node, target_node):
            yield chunk

        for target_node in nodes:
            for value_node in visitor.process_node_with_definition(
                    state, node, self.value):
                yield value_node
            for chunk in self.visit_subnode(visitor, state, node, target_node):
                yield chunk


class Optional(Token):
    """
    Optional text, depending on the node having an attribute

    attr
        the attr that is required for the statement to execute
    value
        the token definition segment to be executed
    """

    def __call__(self, visitor, state, node):
        if getattr(node, self.attr) is None:
            return

        # self.value is the definition
        for chunk in visitor.process_node_with_definition(
                state, node, self.value):
            yield chunk


class Operator(Attr):
    """
    An operator symbol
    """

    # TODO figure out how to yield it in a way that tags this as an
    # operator, so that it can be properly normalized by the state base
    # tracker class. (i.e. no space before ':' but after, no space
    # between + iff not followed by unary +/++)

    def _getattr(self, state, node):
        if self.attr:
            return getattr(node, self.attr)
        else:
            return self.value


def node_handler_null(state, node, subnode, token):
    return iter([])


def node_handler_str_default(state, node, subnode, token):
    if isinstance(token.pos, int):
        _, lineno, colno = node.getpos(subnode, token.pos)
    else:
        lineno, colno = None, None
    yield (subnode, lineno, colno, None)


def node_handler_space_imply(state, node, subnode, token):
    yield (' ', 0, 0, None)


def node_handler_space_drop(state, node, subnode, token):
    yield (' ', None, None, None)


def node_handler_newline_simple(state, node, subnode, token):
    yield ('\n', 0, 0, None)


class PrettyPrintStateBase(object):
    """
    Pretty Printer State base class.  Implementation specific, all
    visitor state information are to be stored within instance of
    this class.
    """

    def __init__(self, handlers):
        self.__handlers = {}
        self.__handlers.update(handlers)

    def __call__(self, node, subnode, token):
        handler = self.__handlers.get(type(subnode))
        if handler:
            for chunk in handler(self, node, subnode, token):
                yield chunk
        else:
            raise NotImplementedError


children_newline = JoinAttr(iter, value=(newline,))
children_comma = JoinAttr(iter, value=(Text(value=','), space,))

value = (
    Attr('value'),
)

definitions = {
    'ES5Program': (
        children_newline,
    ),
    'Block': (
        Text(value='{'), newline,
        indent,
        children_newline,
        dedent,
        Text(value='}'), newline,
    ),
    'VarStatement': (
        Text(value='var'), space, children_comma, Text(value=';'),
    ),
    'VarDecl': (
        Attr('identifier'), Optional('initializer', (
            Operator(value='='), Attr('initializer'),),),
    ),
    'VarDeclNoIn': (
        Text(value='var '), Attr('identifier'), Optional('initializer', (
            Operator(value='='), Attr('initializer'),),),
    ),
    'GroupingOp': (
        Text(value='('), Attr('expr'), Text(value=')'),
    ),
    'Identifier': value,
    'Assign': (
        Attr('left'), optional_space, Attr('op'), space, Attr('right'),
    ),
    'GetPropAssign': (
        Text(value='get '), Attr('prop_name'), Text(value='()'), space,
        Text(value='{'), newline,
        indent,
        JoinAttr(attr='elements', value=(newline,)),
        dedent,
        Text(value='}'),
    ),
    'SetPropAssign': (
        Text(value='set '), Attr('prop_name'), Text(value='('),
        Attr('parameters'), Text(value=')'), space,
        Text(value='{'), newline,
        indent,
        JoinAttr(attr='elements', value=(newline,)),
        dedent,
        Text(value='}'),
    ),
    'Number': value,
    'Comma': (
        Attr('left'), Text(value=','), space, Attr('right'),
    ),
    'EmptyStatement': value,
    'If': (
        Text(value='if'), space,
        Text(value='('), Attr('predicate'), Text(value=')'), space,
        Attr('consequent'),
        Optional('alternative', (
            space, Text(value='else'), space, Attr('alternative'),)),
    ),
    'Boolean': value,
    'For': (
        Text(value='for'), space, Text(value='('),
        Attr('init'), Attr('cond'), Attr('count'), Text(value=')'),
        Attr('statement'),
    ),
    'ForIn': (
        Text(value='for'), space, Text(value='('),
        Attr('item'), Attr('iterable'), Text(value=')'),
        Attr('statement'),
    ),
    'BinOp': (
        Attr('left'), space, Operator(attr='op'), space, Attr('right'),
    ),
    'UnaryOp': (
        Operator(attr='op'), optional_space, Attr('value'),
    ),
    'PostfixExpr': (
        Operator(attr='value'), Attr('op'),
    ),
    'ExprStatement': (
        Attr('expr'), Text(value=';'),
    ),
    'DoWhile': (
        Text(value='do'), space, Attr('statement'),
        Text(value='while'), space, Text(value='('),
        Attr('predicate'), Text(value=');'),
    ),
    'While': (
        Text(value='while'), space,
        Text(value='('), Attr('predicate'), Text(value=')'),
        Attr('statement'),
    ),
    'Null': (
        Text(value='null'),
    ),
    'String': (
        Attr(attr='value'),
    ),
    'Continue': (
        Text(value='continue'), Optional('identifier', (
            space, Attr(attr='identifier'))), Text(value=';'),
    ),
    'Break': (
        Text(value='break'), Optional('identifier', (
            space, Attr(attr='identifier'))), Text(value=';'),
    ),
    'Return': (
        Text(value='return'), Optional('expr', (
            space, Attr(attr='expr'))), Text(value=';'),
    ),
    'With': (
        Text(value='with'), space,
        Text(value='('), Attr('expr'), Text(value=')'), space,
        Attr('statement'),
    ),
    'Label': (
        Attr('identifier'), Text(value=':'), space, Attr('statement'),
    ),
    'Switch': (
        Text(value='switch'), space,
        Text(value='('), Attr('expr'), Text(value=')'), space, Text(value='{'),
        newline, indent,
        Attr('cases'),
        Optional('default', (Attr('default'))),
        newline, dedent,
        Text(value='}'),
    ),
    'Case': (
        Text(value='case'), space, Attr('expr'), Text(value=':'),
        newline, indent,
        JoinAttr('elements', value=(newline,)),
        newline, dedent,
    ),
    'Default': (
        Text(value='default:'), newline, indent,
        JoinAttr('elements', value=(newline,)),
        newline, dedent,
    ),
    'Throw': (
        Text(value='throw'), space, Attr('expr'),
    ),
    'Debugger': (
        Text(value='debugger;'),
    ),
    'Try': (
        Text(value='try'), space, Attr('statements'),
        Optional('catch', (space, Attr('catch'))),
        Optional('fin', (space, Attr('fin'))),
    ),
    'Catch': (
        Text(value='catch'), space,
        Text(value='('), Attr('identifier'), Text(value=')'), space,
        Attr('elements'),
    ),
    'Finally': (
        Text(value='finally'), space, Attr('elements'),
    ),
    'FuncDecl': (
        Text(value='function'), space, Attr('identifier'),
        Text(value='('),
        JoinAttr('parameters', value=(Text(value=','), space)),
        Text(value=')'), space,
        Text(value='{'), newline,
        indent,
        JoinAttr('elements', value=(newline,)), newline,
        dedent,
        Text(value='}'),
    ),
    'FuncExpr': (
        Text(value='function'), space, Attr('identifier'),
        Text(value='('),
        JoinAttr('parameters', value=(Text(value=','), space,)),
        Text(value=')'), space,
        Text(value='{'), newline,
        indent,
        JoinAttr('elements', value=(newline,)), newline,
        dedent,
        Text(value='}'),
    ),
    'Conditional': (
        Attr('predicate'), space, Text(value='?'), space,
        Attr('consequent'), space, Text(value=':'), space,
        Attr('alternative'),
    ),
    'Regex': value,
    'NewExpr': (
        Text(value='new '), Attr('identifier'), Text(value='('),
        JoinAttr('args', value=(Text(value=','), space)),
        Text(value=')'),
    ),
    'DotAccessor': (
        Attr('node'), Text(value='.'), Attr('identifier'),
    ),
    'BracketAccessor': (
        Attr('node'), Text(value='['), Attr('expr'), Text(value=']'),
    ),
    'FunctionCall': (
        Attr('identifier'), Text(value='('),
        JoinAttr('args', value=(Text(value=','), space)),
        Text(value=')'),
    ),
    'Object': (
        Text(value='{'), newline,
        indent,
        JoinAttr('properties', value=(Text(value=','), newline,)), newline,
        dedent,
        Text(value='}'),
    ),
    'Array': (
        Text(value='['),
        JoinAttr('items', value=(Text(value=','), space,)),
        Text(value=']'),
    ),
    'Elision': (
    ),
    'This': (
        Text(value='this'),
    ),
}


class BaseVisitor(object):
    """
    Base ES5 visitor
    """

    def __init__(self, indent=2, handlers=None, definitions=definitions):
        """
        Optional arguements

        indent
            level of indentation in spaces to record; defaults to 2.
        handlers
            optional handlers, where the key is the name of the node
            subclass, value being the callable that will return the
            nodes in the right order.
        """

        self.indent = indent
        self.handlers = self.default_handlers()
        if handlers:
            self.handlers.update(handlers)
        self.definitions = {}
        self.definitions.update(definitions)

    def default_handlers(self):
        return {
            str: node_handler_str_default,
            Space: node_handler_space_imply,
            OptionalSpace: node_handler_space_imply,
            Newline: node_handler_newline_simple,
            Indent: node_handler_null,
            Dedent: node_handler_null,
        }

    def process_node_with_definition(self, state, node, definition):
        for token in definition:
            if callable(token):
                gen = token(self, state, node)
            else:
                gen = state(node, token, token)
            for chunk in gen:
                yield chunk

    def visit(self, state, node):
        key = node.__class__.__name__
        for chunk in self.process_node_with_definition(
                state, node, self.definitions[key]):
            yield chunk

    def __call__(self, node):
        state = PrettyPrintStateBase(self.handlers)
        for chunk in self.visit(state, node):
            yield chunk
