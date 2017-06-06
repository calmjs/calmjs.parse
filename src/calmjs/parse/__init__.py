# -*- coding: utf-8 -*-
"""
Quick access helper functions
"""

from calmjs.parse.parsers.es5 import Parser as ES5Parser


def es5(source):
    """
    Return an AST from the input ES5 source.
    """

    return ES5Parser().parse(source)
