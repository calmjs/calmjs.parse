# -*- coding: utf-8 -*-
"""
Specialized lexer token subclasses.
"""

from ply.lex import LexToken


class AutoLexToken(LexToken):
    """
    Special type for automatically generated tokens.
    """
