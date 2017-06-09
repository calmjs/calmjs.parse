# -*- coding: utf-8 -*-
"""
Helpers that will forcibly regenerate the tab files.

The original goal of this was to force the creation of tab files using
the utf8 codec to workaround issues with the ply package, for systems
that do not have utf8 configured as the default codec.
"""

import codecs
import sys
from functools import partial
from os import unlink
from os.path import exists
from ply import lex
from importlib import import_module

# have to do this for every parser modules
from calmjs.parse.parsers import es5


def purge_tabs(module):
    paths = []
    for entry in ('lextab', 'yacctab'):
        # we assume the specified entries are defined as such
        name = getattr(module, entry)
        if entry not in name:
            # this really prevents this method from being a thing to
            # unlink other modules.
            raise ValueError(
                'provided module `%s` does not export expected tab values ' %
                module.__name__
            )
        try:
            import_module(name)
        except ImportError:
            # don't need to do anything
            pass
        else:
            paths.append(sys.modules.pop(name).__file__)

    unlink_modules(verify_paths(paths))


def verify_paths(paths):
    for path in paths:
        if exists(path):
            yield path
        if path[-4:] in ('.pyc', '.pyo'):
            # find the .py file, too.
            if exists(path[:-1]):
                yield path[:-1]


def unlink_modules(paths):
    for path in paths:
        # will raise whatever error, i.e. when insufficient permission
        unlink(path)


def reoptimize(module):
    purge_tabs(module)
    # create a new parser should rengenerate the module
    module.Parser()


def reoptimize_all(monkey_patch=False):
    if monkey_patch:
        lex.open = partial(codecs.open, encoding='utf8')
    modules = (es5,)
    for module in modules:
        reoptimize(module)


if __name__ == '__main__':  # pragma: no cover
    reoptimize_all(True)
