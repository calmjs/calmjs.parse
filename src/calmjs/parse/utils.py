# -*- coding: utf-8 -*-
"""
Various utilities and helpers
"""

import sys
from os.path import dirname
from os.path import isabs
from os.path import normpath
from os.path import relpath

try:
    from pkg_resources import working_set
    from pkg_resources import Requirement
    ply_dist = working_set.find(Requirement.parse('ply'))
except ImportError:  # pragma: no cover
    ply_dist = None

py_major = sys.version_info.major
unicode = unicode if py_major < 3 else None  # noqa: F821
str = str if sys.version_info.major > 2 else unicode  # noqa: F821


def repr_compat(s):
    """
    Since Python 2 is annoying with unicode literals, and that we are
    enforcing the usage of unicode, this ensures the repr doesn't spew
    out the unicode literal prefix.
    """

    if unicode and isinstance(s, unicode):
        return repr(s)[1:]
    else:
        return repr(s)


def generate_tab_names(name):
    """
    Return the names to lextab and yacctab modules for the given module
    name.  Typical usage should be like so::

    >>> lextab, yacctab = generate_tab_names(__name__)
    """

    package_name, module_name = name.rsplit('.', 1)

    version = ply_dist.version.replace(
        '.', '_') if ply_dist is not None else 'unknown'
    data = (package_name, module_name, py_major, version)
    lextab = '%s.lextab_%s_py%d_ply%s' % data
    yacctab = '%s.yacctab_%s_py%d_ply%s' % data
    return lextab, yacctab


def format_lex_token(token):
    return '%s at %s:%s' % (
        repr_compat(token.value), token.lineno, getattr(token, 'colno', '?'))


def normrelpath(base, target):
    """
    This function takes the base and target arguments as paths, and
    returns an equivalent relative path from base to the target, if both
    provided paths are absolute.
    """

    if not all(map(isabs, [base, target])):
        return target

    return relpath(normpath(target), dirname(normpath(base)))
