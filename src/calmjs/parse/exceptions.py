# -*- coding: utf-8 -*-
"""
Provide a subclass to distinguish ECMA syntax errors from the default.
"""


class ECMASyntaxError(SyntaxError):
    """
    Syntax error for ECMA parsing.
    """


class ECMARegexSyntaxError(ECMASyntaxError):
    """
    Syntax error for ECMA regex.
    """


class ProductionError(Exception):
    """
    During the production stage, if a syntax error was produced, raising
    SyntaxError will result in ply trying to handle errors, so for that
    a wrapper exception is needed.
    """
