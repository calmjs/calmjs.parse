# -*- coding: utf-8 -*-
"""
Various utilities and helpers
"""

import sys

try:
    from pkg_resources import working_set
    from pkg_resources import Requirement
    ply_dist = working_set.find(Requirement.parse('ply'))
except ImportError:  # pragma: no cover
    ply_dist = None

py_major = sys.version_info.major


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
