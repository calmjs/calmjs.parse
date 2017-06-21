# -*- coding: utf-8 -*-
"""
ES5 base visitors
"""

from calmjs.parse.pptypes import (
    Space,
    OptionalSpace,
    Newline,
    OptionalNewline,
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
)
from calmjs.parse.visitors.layout import (
    token_handler_str_default,
    layout_handler_space_imply,
    layout_handler_newline_optional_pretty,
    layout_handler_newline_simple,
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,
)

# other helpful shorthands.
children_newline = JoinAttr(iter, value=(Newline,))
children_comma = JoinAttr(iter, value=(Text(value=','), Space,))
value = (
    Attr('value'),
)

# definitions of all the rules for all the types for an ES5 program.
definitions = {
    'ES5Program': (
        children_newline,
        OptionalNewline,
    ),
    'Block': (
        Text(value='{'),
        Indent, Newline,
        children_newline,
        Dedent, Newline,
        Text(value='}'), Newline,
    ),
    'VarStatement': (
        Text(value='var'), Space, children_comma, Text(value=';'),
    ),
    'VarDecl': (
        Attr('identifier'), Optional('initializer', (
            Space, Operator(value='='), Space, Attr('initializer'),),),
    ),
    'VarDeclNoIn': (
        Text(value='var '), Attr('identifier'), Optional('initializer', (
            Space, Operator(value='='), Space, Attr('initializer'),),),
    ),
    'GroupingOp': (
        Text(value='('), Attr('expr'), Text(value=')'),
    ),
    'Identifier': value,
    'Assign': (
        Attr('left'), OptionalSpace, Attr('op'), Space, Attr('right'),
    ),
    'GetPropAssign': (
        Text(value='get '), Attr('prop_name'), Text(value='()'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr(attr='elements', value=(Newline,)),
        Dedent, Newline,
        Text(value='}'),
    ),
    'SetPropAssign': (
        Text(value='set '), Attr('prop_name'), Text(value='('),
        Attr('parameters'), Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr(attr='elements', value=(Newline,)),
        Dedent, Newline,
        Text(value='}'),
    ),
    'Number': value,
    'Comma': (
        Attr('left'), Text(value=','), Space, Attr('right'),
    ),
    'EmptyStatement': value,
    'If': (
        Text(value='if'), Space,
        Text(value='('), Attr('predicate'), Text(value=')'), Space,
        Attr('consequent'),
        Optional('alternative', (
            Space, Text(value='else'), Space, Attr('alternative'),)),
    ),
    'Boolean': value,
    'For': (
        Text(value='for'), Space, Text(value='('),
        Attr('init'), Attr('cond'), Attr('count'), Text(value=')'),
        Attr('statement'),
    ),
    'ForIn': (
        Text(value='for'), Space, Text(value='('),
        Attr('item'), Attr('iterable'), Text(value=')'),
        Attr('statement'),
    ),
    'BinOp': (
        Attr('left'), Space, Operator(attr='op'), Space, Attr('right'),
    ),
    'UnaryOp': (
        Operator(attr='op'), OptionalSpace, Attr('value'),
    ),
    'PostfixExpr': (
        Operator(attr='value'), Attr('op'),
    ),
    'ExprStatement': (
        Attr('expr'), Text(value=';'),
    ),
    'DoWhile': (
        Text(value='do'), Space, Attr('statement'),
        Text(value='while'), Space, Text(value='('),
        Attr('predicate'), Text(value=');'),
    ),
    'While': (
        Text(value='while'), Space,
        Text(value='('), Attr('predicate'), Text(value=')'), Space,
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
            Space, Attr(attr='identifier'))), Text(value=';'),
    ),
    'Break': (
        Text(value='break'), Optional('identifier', (
            Space, Attr(attr='identifier'))), Text(value=';'),
    ),
    'Return': (
        Text(value='return'), Optional('expr', (
            Space, Attr(attr='expr'))), Text(value=';'),
    ),
    'With': (
        Text(value='with'), Space,
        Text(value='('), Attr('expr'), Text(value=')'), Space,
        Attr('statement'),
    ),
    'Label': (
        Attr('identifier'), Text(value=':'), Space, Attr('statement'),
    ),
    'Switch': (
        Text(value='switch'), Space,
        Text(value='('), Attr('expr'), Text(value=')'), Space, Text(value='{'),
        Indent, Newline,
        Attr('cases'),
        Optional('default', (Attr('default'))),
        Dedent, Newline,
        Text(value='}'),
    ),
    'Case': (
        Text(value='case'), Space, Attr('expr'), Text(value=':'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, Newline,
    ),
    'Default': (
        Text(value='default:'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, Newline,
    ),
    'Throw': (
        Text(value='throw'), Space, Attr('expr'),
    ),
    'Debugger': (
        Text(value='debugger;'),
    ),
    'Try': (
        Text(value='try'), Space, Attr('statements'),
        Optional('catch', (Space, Attr('catch'))),
        Optional('fin', (Space, Attr('fin'))),
    ),
    'Catch': (
        Text(value='catch'), Space,
        Text(value='('), Attr('identifier'), Text(value=')'), Space,
        Attr('elements'),
    ),
    'Finally': (
        Text(value='finally'), Space, Attr('elements'),
    ),
    'FuncDecl': (
        Text(value='function'), Space, Attr('identifier'),
        Text(value='('),
        JoinAttr('parameters', value=(Text(value=','), Space)),
        Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, Newline,
        Text(value='}'),
    ),
    'FuncExpr': (
        Text(value='function'), Space, Attr('identifier'),
        Text(value='('),
        JoinAttr('parameters', value=(Text(value=','), Space,)),
        Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, Newline,
        Text(value='}'),
    ),
    'Conditional': (
        Attr('predicate'), Space, Text(value='?'), Space,
        Attr('consequent'), Space, Text(value=':'), Space,
        Attr('alternative'),
    ),
    'Regex': value,
    'NewExpr': (
        Text(value='new '), Attr('identifier'), Text(value='('),
        JoinAttr('args', value=(Text(value=','), Space)),
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
        JoinAttr('args', value=(Text(value=','), Space)),
        Text(value=')'),
    ),
    'Object': (
        Text(value='{'),
        Indent, Newline,
        JoinAttr('properties', value=(Text(value=','), Newline,)),
        Dedent, Newline,
        Text(value='}'),
    ),
    'Array': (
        Text(value='['),
        JoinAttr('items', value=(Text(value=','), Space,)),
        Text(value=']'),
    ),
    'Elision': (
    ),
    'This': (
        Text(value='this'),
    ),
}


def default_layout_handlers():
    return {
        Space: layout_handler_space_imply,
        OptionalSpace: layout_handler_space_optional_pretty,
        Newline: layout_handler_newline_simple,
        OptionalNewline: layout_handler_newline_optional_pretty,
    }


def minimum_layout_handlers():
    return {
        Space: layout_handler_space_minimum,
        OptionalSpace: layout_handler_space_minimum,
    }


class BaseVisitor(object):
    """
    A simple base visitor class built upon the pprint helpers.
    """

    def __init__(
            self,
            indent=2,
            token_handler=token_handler_str_default,
            layouts=(default_layout_handlers,),
            layout_handlers=None,
            definitions=definitions):
        """
        Optional arguements

        indent
            level of indentation in spaces to record; defaults to 2.
        token_handler
            passed onto the state object; this is the handler that will
            process
        layouts
            An tuple of callables that will provide the setup of
            indentation.  The callables must return a layout_handlers
            mapping, which is a dict with the key being the layout class
            and the value being the callable that accept a
            PrettyPrintState instance, a Node, before and after chunk.
        layout_handlers
            Additional layout handlers, given in the mapping that was
            described above.
        """

        self.indent = indent
        self.token_handler = token_handler
        self.layout_handlers = {}
        for layout in layouts:
            self.layout_handlers.update(layout())
        if layout_handlers:
            self.layout_handlers.update(layout_handlers)
        self.definitions = {}
        self.definitions.update(definitions)

    def __call__(self, node):
        state = PrettyPrintState(
            self.token_handler, self.layout_handlers, self.definitions)
        for chunk in pretty_print_visitor(state, node, state[node]):
            yield chunk
