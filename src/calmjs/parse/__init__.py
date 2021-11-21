# -*- coding: utf-8 -*-
"""
Quick access helper functions
"""

try:
    from calmjs.parse.factory import ParserUnparserFactory
except ImportError as e:  # pragma: no cover
    exc = e

    def import_error(*a, **kw):
        raise exc

    es5 = import_error
else:
    es5 = ParserUnparserFactory('es5', 'pretty_print', 'minify_print')
