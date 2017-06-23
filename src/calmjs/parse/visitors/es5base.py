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
    ElisionToken,
    ElisionJoinAttr,
)
from calmjs.parse.visitors.pprint import (
    PrettyPrintState,
    pretty_print_visitor,
)
from calmjs.parse.visitors.layout import (
    rule_handler_noop,
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
        Dedent, OptionalNewline,
        Text(value='}'),
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
        Text(value='get'), Space, Attr('prop_name'),
        Text(value='('), Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr(attr='elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
    ),
    'SetPropAssign': (
        Text(value='set'), Space, Attr('prop_name'), Text(value='('),
        Attr('parameters'), Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr(attr='elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
    ),
    'Number': value,
    'Comma': (
        Attr('left'), Text(value=','), Space, Attr('right'),
    ),
    'EmptyStatement': value,
    'If': (
        Text(value='if'), Space,
        Text(value='('), Attr('predicate'), Text(value=')'), OptionalSpace,
        Attr('consequent'),
        Optional('alternative', (
            Newline, Text(value='else'), OptionalSpace, Attr('alternative'),)),
    ),
    'Boolean': value,
    'For': (
        Text(value='for'), Space, Text(value='('),
        Attr('init'),
        OptionalSpace, Attr('cond'),
        OptionalSpace, Attr('count'),
        Text(value=')'), OptionalSpace, Attr('statement'),
    ),
    'ForIn': (
        Text(value='for'), Space, Text(value='('),
        Attr('item'),
        Space, Text(value='in'), Space,
        Attr('iterable'), Text(value=')'), OptionalSpace, Attr('statement'),
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
        Text(value='do'), Space, Attr('statement'), Space,
        Text(value='while'), Space, Text(value='('),
        Attr('predicate'), Text(value=');'),
    ),
    'While': (
        Text(value='while'), Space,
        Text(value='('), Attr('predicate'), Text(value=')'), OptionalSpace,
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
    'SwitchStatement': (
        Text(value='switch'), Space,
        Text(value='('), Attr('expr'), Text(value=')'), Space,
        Attr('case_block'),
    ),
    'CaseBlock': (
        Text(value='{'),
        Indent, Newline,
        children_newline,
        Dedent, OptionalNewline,
        Text(value='}'),
    ),
    'Case': (
        Text(value='case'), Space, Attr('expr'), Text(value=':'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent,
    ),
    'Default': (
        Text(value='default'), Text(value=':'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent,
    ),
    'Throw': (
        Text(value='throw'), Space, Attr('expr'), Text(value=';'),
    ),
    'Debugger': (
        Text(value='debugger'), Text(value=';'),
    ),
    'Try': (
        Text(value='try'), Space, Attr('statements'),
        Optional('catch', (Newline, Attr('catch'),)),
        Optional('fin', (Newline, Attr('fin'),)),
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
        Text(value='function'), Optional('identifier', (Space,)),
        Attr('identifier'), Text(value='('),
        JoinAttr('parameters', value=(Text(value=','), Space)),
        Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
    ),
    'FuncExpr': (
        Text(value='function'), Optional('identifier', (Space,)),
        Attr('identifier'), Text(value='('),
        JoinAttr('parameters', value=(Text(value=','), Space,)),
        Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
    ),
    'Conditional': (
        Attr('predicate'), Space, Text(value='?'), Space,
        Attr('consequent'), Space, Text(value=':'), Space,
        Attr('alternative'),
    ),
    'Regex': value,
    'NewExpr': (
        Text(value='new'), Space, Attr('identifier'), Attr('args'),
    ),
    'DotAccessor': (
        Attr('node'), Text(value='.'), Attr('identifier'),
    ),
    'BracketAccessor': (
        Attr('node'), Text(value='['), Attr('expr'), Text(value=']'),
    ),
    'FunctionCall': (
        Attr('identifier'), Attr('args'),
    ),
    'Arguments': (
        Text(value='('),
        JoinAttr('items', value=(Text(value=','), Space)),
        Text(value=')'),
    ),
    'Object': (
        Text(value='{'),
        Optional('properties', (
            Indent, Newline,
            JoinAttr('properties', value=(Text(value=','), Newline,)),
            Dedent, Newline,
        )),
        Text(value='}'),
    ),
    'Array': (
        Text(value='['),
        ElisionJoinAttr('items', value=(Space,)),
        Text(value=']'),
    ),
    'Elision': (
        ElisionToken(attr='value', value=','),
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
        # if an indent is immediately followed by dedent without actual
        # content, simply do nothing.
        (Indent, Newline, Dedent): rule_handler_noop,
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
            self.definitions, self.token_handler, self.layout_handlers)
        for chunk in pretty_print_visitor(state, node, state[node]):
            yield chunk
