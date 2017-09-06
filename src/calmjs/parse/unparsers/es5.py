# -*- coding: utf-8 -*-
"""
Description for ES5 unparser.
"""

from __future__ import unicode_literals
from calmjs.parse.lexers.es5 import Lexer

from calmjs.parse.ruletypes import (
    Space,
    RequiredSpace,
    OptionalSpace,
    Newline,
    OptionalNewline,
    Indent,
    Dedent,
    PushScope,
    PopScope,
    PushCatch,
    PopCatch,
)
from calmjs.parse.ruletypes import (
    Attr,
    Text,
    Optional,
    JoinAttr,
    Operator,
    ElisionToken,
    ElisionJoinAttr,
)
from calmjs.parse.ruletypes import (
    Declare,
    Resolve,
)
from calmjs.parse.ruletypes import (
    children_newline,
    children_comma,
)
from calmjs.parse.unparsers.base import BaseUnparser
from calmjs.parse import rules

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
        Attr(Declare('identifier')), Optional('initializer', (
            Space, Operator(value='='), Space, Attr('initializer'),),),
    ),
    'VarDeclNoIn': (
        Text(value='var '), Attr(Declare('identifier')),
        Optional('initializer', (
            Space, Operator(value='='), Space, Attr('initializer'),),),
    ),
    'GroupingOp': (
        Text(value='('), Attr('expr'), Text(value=')'),
    ),
    'Identifier': (Attr(Resolve()),),
    'PropIdentifier': value,
    'Assign': (
        Attr('left'), OptionalSpace, Attr('op'), Space, Attr('right'),
    ),
    'GetPropAssign': (
        Text(value='get'), Space, Attr('prop_name'),
        PushScope,
        Text(value='('), Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr(attr='elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
        PopScope,
    ),
    'SetPropAssign': (
        Text(value='set'), Space, Attr('prop_name'), Text(value='('),
        PushScope,
        Attr(Declare('parameters')), Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr(attr='elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
        PopScope,
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
    'UnaryExpr': (
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
        # should _really_ have a token for logging a warning
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/
        #   Reference/Statements/with
        Text(value='('), Attr('expr'), Text(value=')'), Space,
        Attr('statement'),
    ),
    'Label': (
        Attr('identifier'), Text(value=':'), Space, Attr('statement'),
    ),
    'Switch': (
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
        PushCatch,
        Text(value='('), Attr('identifier'), Text(value=')'), Space,
        Attr('elements'),
        PopCatch,
    ),
    'Finally': (
        Text(value='finally'), Space, Attr('elements'),
    ),
    'FuncDecl': (
        Text(value='function'), Optional('identifier', (RequiredSpace,)),
        Attr(Declare('identifier')), Text(value='('),
        PushScope,
        JoinAttr(Declare('parameters'), value=(Text(value=','), Space)),
        Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
        PopScope,
    ),
    'FuncExpr': (
        Text(value='function'), Optional('identifier', (RequiredSpace,)),
        Attr(Declare('identifier')), Text(value='('),
        PushScope,
        JoinAttr(Declare('parameters'), value=(Text(value=','), Space,)),
        Text(value=')'), Space,
        Text(value='{'),
        Indent, Newline,
        JoinAttr('elements', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value='}'),
        PopScope,
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


class Unparser(BaseUnparser):

    def __init__(
            self,
            definitions=definitions,
            token_handler=None,
            rules=(rules.default(),),
            layout_handlers=None,
            deferrable_handlers=None,
            prewalk_hooks=()):

        super(Unparser, self).__init__(
            definitions=definitions,
            token_handler=token_handler,
            rules=rules,
            layout_handlers=layout_handlers,
            deferrable_handlers=deferrable_handlers,
            prewalk_hooks=(),
        )


def pretty_printer(indent_str='    '):
    """
    Construct a pretty printing unparser
    """

    return Unparser(rules=(rules.indent(indent_str=indent_str),))


def pretty_print(ast, indent_str='  '):
    """
    Simple pretty print function; returns a string rendering of an input
    AST of an ES5 Program.

    arguments

    ast
        The AST to pretty print
    indent_str
        The string used for indentations.  Defaults to two spaces.
    """

    return ''.join(chunk.text for chunk in pretty_printer(indent_str)(ast))


def minify_printer(obfuscate=False, obfuscate_globals=False):
    """
    Construct a minimum printer.
    """

    return Unparser(rules=(
        rules.obfuscate(obfuscate_globals, reserved_keywords=(
            Lexer.keywords_dict.keys())),)
        if obfuscate else (rules.minimum(),))


def minify_print(ast, obfuscate=False, obfuscate_globals=False):
    """
    Simple minify print function; returns a string rendering of an input
    AST of an ES5 program

    Arguments

    ast
        The AST to minify print
    obfuscate
        If True, obfuscate identifiers nested in each scope with a
        shortened identifier name to further reduce output size.

        Defaults to False.
    obfuscate_globals
        Also do the same to identifiers nested on the global scope; do
        not enable unless the renaming of global variables in a not
        fully deterministic manner into something else is guaranteed to
        not cause problems with the generated code and other code that
        in the same environment that it will be executed in.

        Defaults to False for the reason above.
    """

    return ''.join(chunk.text for chunk in minify_printer(
        obfuscate, obfuscate_globals)(ast))
