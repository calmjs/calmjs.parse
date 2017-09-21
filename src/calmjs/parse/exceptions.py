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
