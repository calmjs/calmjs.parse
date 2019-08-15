# -*- coding: utf-8 -*-
"""
Rules setup functions for standard Unparser constructors.  All functions
here return a rule setup function that returns a working and complete
set of handlers for the desired functionality as designed.  While the
rules defined here can mix, note that the Unparser will treat the later
rules as having prescedence for any rule conflicts.
"""

from calmjs.parse.ruletypes import (
    OpenBlock,
    CloseBlock,
    EndStatement,
    Space,
    OptionalSpace,
    RequiredSpace,
    Newline,
    OptionalNewline,
    Indent,
    Dedent,
    Resolve,
    Literal,

    LineComment,
    BlockComment,
)
from calmjs.parse.handlers.core import (
    rule_handler_noop,

    token_handler_unobfuscate,

    layout_handler_openbrace,
    layout_handler_closebrace,
    layout_handler_semicolon,
    layout_handler_semicolon_optional,

    layout_handler_space_imply,
    layout_handler_space_optional_pretty,
    layout_handler_space_minimum,

    deferrable_handler_literal_continuation,
    deferrable_handler_comment,

    default_rules,
    minimum_rules,
)
from calmjs.parse.handlers.indentation import Indentator
from calmjs.parse.handlers.obfuscation import Obfuscator

__all__ = ['default', 'minimum', 'minify', 'indent', 'obfuscate']


def default():
    """
    A default set of handlers
    """

    return default_rules


def minimum():
    """
    The minimum required set of handlers for the results to still be
    considered valid code.  This is due to the fact that a set of
    minimum whitespace handlers are still needed.
    """

    return minimum_rules


def minify(drop_semi=True):
    """
    Rules for minifying output.

    Arguments:

    drop_semi
        Drop semicolons whenever possible.  Note that if Dedent and
        OptionalNewline has a handler defined, it will stop final break
        statements from being resolved due to reliance on normalized
        resolution.

    """

    layout_handlers = {
        OpenBlock: layout_handler_openbrace,
        CloseBlock: layout_handler_closebrace,
        EndStatement: layout_handler_semicolon,
        Space: layout_handler_space_minimum,
        OptionalSpace: layout_handler_space_minimum,
        RequiredSpace: layout_handler_space_imply,
        (Space, OpenBlock): layout_handler_openbrace,
        (Space, EndStatement): layout_handler_semicolon,
        (OptionalSpace, EndStatement): layout_handler_semicolon,
    }

    if drop_semi:
        # if these are defined, they should be dropped; should really
        # provide these as a flag.
        # layout_handlers.update({
        #     OptionalNewline: None,
        #     Dedent: None,
        # })

        layout_handlers.update({
            EndStatement: layout_handler_semicolon_optional,

            # these two rules rely on the normalized resolution
            (OptionalSpace, EndStatement): layout_handler_semicolon_optional,
            (EndStatement, CloseBlock): layout_handler_closebrace,

            # this is a fallback rule for when Dedent is defined by
            # some other rule, which won't neuter all optional
            # semicolons.
            (EndStatement, Dedent): rule_handler_noop,
            ((OptionalSpace, EndStatement), CloseBlock):
                layout_handler_closebrace,
        })

    def minify_rule():
        return {
            'layout_handlers': layout_handlers,
            'deferrable_handlers': {
                Literal: deferrable_handler_literal_continuation,
            },
        }

    return minify_rule


def indent(indent_str=None):
    """
    A complete, standalone indent ruleset.

    Arguments:

    indent_str
        The string used for indentation.  Defaults to None, which will
        defer the value used to the one provided by the Dispatcher.
    """

    def indentation_rule():
        inst = Indentator(indent_str)
        return {'layout_handlers': {
            OpenBlock: layout_handler_openbrace,
            CloseBlock: layout_handler_closebrace,
            EndStatement: layout_handler_semicolon,
            Space: layout_handler_space_imply,
            OptionalSpace: layout_handler_space_optional_pretty,
            RequiredSpace: layout_handler_space_imply,
            Indent: inst.layout_handler_indent,
            Dedent: inst.layout_handler_dedent,
            Newline: inst.layout_handler_newline,
            OptionalNewline: inst.layout_handler_newline_optional,
            (Space, OpenBlock): NotImplemented,
            (Space, EndStatement): layout_handler_semicolon,
            (OptionalSpace, EndStatement): layout_handler_semicolon,
            (Indent, Newline, Dedent): rule_handler_noop,
        }, 'deferrable_handlers': {
            LineComment: deferrable_handler_comment,
            BlockComment: deferrable_handler_comment,
        }}
    return indentation_rule


def obfuscate(
        obfuscate_globals=False,
        shadow_funcname=False,
        reserved_keywords=()):
    """
    The name obfuscation ruleset.

    Arguments:

    obfuscate_globals
        If true, identifier names on the global scope will also be
        obfuscated.  Default is False.
    shadow_funcname
        If True, permit the shadowing of the name of named functions by
        names within the scope it defines.  Default is False.
    reserved_keywords
        A tuple of strings that should not be generated as obfuscated
        identifiers.
    """

    def name_obfuscation_rules():
        inst = Obfuscator(
            obfuscate_globals=obfuscate_globals,
            shadow_funcname=shadow_funcname,
            reserved_keywords=reserved_keywords,
        )
        return {
            'token_handler': token_handler_unobfuscate,
            'layout_handlers': {
            },
            'deferrable_handlers': {
                Resolve: inst.resolve,
            },
            'prewalk_hooks': [
                inst.prewalk_hook,
            ],
        }
    return name_obfuscation_rules
