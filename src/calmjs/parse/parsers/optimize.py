# -*- coding: utf-8 -*-
"""
Helpers for maintenance/generation of the lextab/yacctab modules.

The original goal of this was to force the creation of tab files using
the utf8 codec to workaround issues with the ply package, for systems
that do not have utf8 configured as the default codec.
"""

import codecs
import sys
from functools import partial
from os import unlink
from os.path import exists
from importlib import import_module


def find_tab_paths(module):
    # return a list of lextab/yacctab module paths and a list of missing
    # import names.
    paths = []
    missing = []
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
            missing.append(name)
        else:
            paths.append(sys.modules.pop(name).__file__)
    return paths, missing


def purge_tabs(module):
    paths, _ = find_tab_paths(module)
    unlink_modules(verify_paths(paths))


def verify_paths(paths):
    for path in paths:
        if exists(path):
            yield path
        # locate any adjacent .py[co]? files based on module path
        # returned; mostly a problem with Python 2
        if path[-4:] in ('.pyc', '.pyo'):
            if exists(path[:-1]):
                yield path[:-1]
        else:
            for c in 'co':
                if exists(path + c):
                    yield path + c


def unlink_modules(paths):
    for path in paths:
        # will raise whatever error, i.e. when insufficient permission
        unlink(path)


def reoptimize(module):
    purge_tabs(module)
    # create a new parser should rengenerate the module
    module.Parser()


def optimize_build(module):
    paths, missing = find_tab_paths(module)
    if missing:
        # only purge and regenerate if any are missing.
        unlink_modules(verify_paths(paths))
        module.Parser()


def reoptimize_all(monkey_patch=False, first_build=False):
    """
    The main optimize method for maintainence of the generated tab
    modules required by ply

    Arguments:

    monkey_patch
        patches the default open function in ply.lex to use utf8

        default: False

    first_build
        flag for switching between reoptimize/optimize_build method;
        setting the flag to True specifies the latter.

        default: False
    """

    if monkey_patch:
        try:
            from ply import lex
        except ImportError:  # pragma: no cover
            pass  # fail later; only fail if import ply is truly needed
        else:
            lex.open = partial(codecs.open, encoding='utf8')

    modules = ('.es5',)
    try:
        for name in modules:
            module = import_module(name, 'calmjs.parse.parsers')
            if first_build:
                optimize_build(module)
            else:
                reoptimize(module)
    except ImportError as e:
        if not first_build or 'ply' not in str(e):
            raise
        sys.stderr.write(
            u"ERROR: cannot import ply, aborting build; please ensure "
            "that the python package 'ply' is installed before attempting to "
            "build this package; please refer to the top level README for "
            "further details\n"
        )
        sys.exit(1)


if __name__ == '__main__':  # pragma: no cover
    reoptimize_all(True, '--build' in sys.argv)
