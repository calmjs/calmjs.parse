# -*- coding: utf-8 -*-
"""
Various utilities and helpers
"""


try:
    from pkg_resources import working_set
    from pkg_resources import Requirement
    ply_dist = working_set.find(Requirement.parse('ply'))
except ImportError:  # pragma: no cover
    ply_dist = None


def generate_tab_names(name):
    """
    Return the names to lextab and yacctab modules for the given module
    name.  Typical usage should be like so::

    >>> lextab, yacctab = generate_tab_names(__name__)
    """

    package_name, module_name = name.rsplit('.', 1)

    version = ply_dist.version.replace(
        '.', '_') if ply_dist is not None else 'unknown'
    lextab = '%s.lextab_%s_%s' % (package_name, module_name, version)
    yacctab = '%s.yacctab_%s_%s' % (package_name, module_name, version)
    return lextab, yacctab
