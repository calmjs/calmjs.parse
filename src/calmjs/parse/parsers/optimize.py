# -*- coding: utf-8 -*-
"""
Helpers for maintenance/generation of the lextab/yacctab modules.

The original goal of this was to force the creation of tab files using
the utf8 codec to workaround issues with the ply package, for systems
that do not have utf8 configured as the default codec.
"""

import codecs
import os
import sys
from functools import partial
from os import unlink
from os.path import exists
from importlib import import_module
from calmjs.parse.utils import generate_tab_names
from calmjs.parse.utils import ply_dist

_ASSUME_PLY_VERSION = '3.11'
_ASSUME_ENVVAR = 'CALMJS_PARSE_ASSUME_PLY_VERSION'


def validate_imports(*imports):
    paths = []
    missing = []
    for name in imports:
        try:
            import_module(name)
        except ImportError:
            missing.append(name)
        else:
            paths.append(sys.modules.pop(name).__file__)
    return paths, missing


def find_tab_paths(module):
    # return a list of lextab/yacctab module paths and a list of missing
    # import names.
    names = []
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
        names.append(name)
    return validate_imports(*names)


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


def _assume_ply_version():
    version = os.environ.get(_ASSUME_ENVVAR, _ASSUME_PLY_VERSION)
    if ply_dist is None:
        if _ASSUME_ENVVAR in os.environ:
            source = "using environment variable %r" % _ASSUME_ENVVAR
        else:
            # allow bypassing of setuptools as ply provides this
            # attribute
            try:
                import ply
                version = ply.__version__
                source = "using value provided by ply"
            except ImportError:  # pragma: no cover
                ply = None
                source = "using default value"

        sys.stderr.write(
            u"WARNING: cannot find distribution for 'ply'; "
            "%s, assuming 'ply==%s' for pre-generated modules\n" % (
                source, version))
    return version


def optimize_build(module_name, assume_ply_version=True):
    """
    optimize build helper for first build

    assume_ply_version
        This flag denotes whether or not to assume a ply version should
        ply be NOT installed; this will either assume ply to be whatever
        value assigned to _ASSUME_PLY_VERSION (i.e. 3.11), or read from
        the environment variable `CALMJS_PARSE_ASSUME_PLY_VERSION`.

        The goal is to allow the build to proceed if the pre-generated
        files are already present, before the dependency resolution at
        the installation time actually kicks in to install ply.

        Default: True
    """

    kws = {}
    if assume_ply_version:
        kws['_version'] = _assume_ply_version()

    lextab, yacctab = generate_tab_names(module_name, **kws)
    paths, missing = validate_imports(lextab, yacctab)
    if missing:
        # only import, purge and regenerate if any are missing.
        unlink_modules(verify_paths(paths))
        module = import_module(module_name)
        # use whatever assumed version or otherwise as set up by
        # the local generation function.
        module.Parser(lextab=lextab, yacctab=yacctab)


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
            if first_build:
                # A consideration for modifying this flag to simply
                # check for a marker file to denote none of this being
                # needed (i.e. this tarball was fully prepared), but it
                # will not solve the issue where the distro packager
                # already got an even more recent version of ply
                # installed (as unlikely as that is) and that build step
                # then is completely skipped.
                optimize_build('calmjs.parse.parsers' + name)
            else:
                module = import_module(name, 'calmjs.parse.parsers')
                reoptimize(module)
    except ImportError as e:
        if not first_build or 'ply' not in str(e):
            raise
        sys.stderr.write(
            u"ERROR: cannot find pre-generated modules for the assumed 'ply' "
            "version from above and/or cannot `import ply` to build generated "
            "modules, aborting build; please either ensure that the source "
            "archive containing the pre-generate modules is being used, or "
            "that the python package 'ply' is installed and available for "
            "import before attempting to use the setup.py to build this "
            "package; please refer to the top level README for further "
            "details\n"
        )
        sys.exit(1)


if __name__ == '__main__':  # pragma: no cover
    reoptimize_all(True, '--build' in sys.argv)
