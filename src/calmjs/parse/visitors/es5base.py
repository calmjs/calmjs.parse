# -*- coding: utf-8 -*-
"""
ES5 base visitors
"""

from calmjs.parse.pptypes import (
    Space,
    OptionalSpace,
    Newline,
    Indent,
    Dedent,
)
from calmjs.parse.pptypes import (
    Attr,
    Text,
    Optional,
    JoinAttr,
    Operator,
)
from calmjs.parse.visitors.pprint import (
    PrettyPrintState,
    pretty_print_visitor,
    node_handler_null,
    node_handler_str_default,
    node_handler_space_imply,
    node_handler_newline_simple,
)

# instantiate the values required for the rule definition.
space = Space()
optional_space = OptionalSpace()
newline = Newline()
indent = Indent()
dedent = Dedent()

# other helpful shorthands.
children_newline = JoinAttr(iter, value=(newline,))
children_comma = JoinAttr(iter, value=(Text(value=','), space,))
value = (
    Attr('value'),
)

# definitions of all the rules for all the types for an ES5 program.
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
    A simple base visitor class built upon the pprint helpers.
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

    def __call__(self, node):
        state = PrettyPrintState(self.handlers, self.definitions)
        for chunk in pretty_print_visitor(state, node, state[node]):
            yield chunk
