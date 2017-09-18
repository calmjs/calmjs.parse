# -*- coding: utf-8 -*-
"""
Generic io functions for use with parsers.
"""

from calmjs.parse import sourcemap


def read(parser, stream):
    """
    Return an AST from the input ES5 stream.
    """

    text = stream.read()
    result = parser(text)
    result.sourcepath = getattr(stream, 'name', None)
    return result


def write(
        unparser, node, output_stream, sourcemap_stream=None,
        sourcemap_normalize_mappings=True,
        sourcemap_normalize_paths=True):
    """
    Write out the node using the unparser into an output stream, and
    optionally the sourcemap using the sourcemap stream.

    Ideally, file objects should be passed to the *_stream arguments, so
    that the name resolution built into the sourcemap builder function
    will be used.  Also, if these file objects are opened using absolute
    path arguments, enabling the sourcemap_normalize_paths flag will
    have all paths normalized to their relative form.

    If the provided streams are not anchored on the filesystem, or that
    the provide node was generated from a string or in-memory stream,
    the generation of the sourcemap should be done using the lower level
    `write` function provided by the sourcemap module, which this method
    wraps.  Alternatively, the top level node should have its sourcepath
    set to path that this node originated from.

    Arguments

    unparser
        An unparser instance.
    node
        The Node to write with.
    output_stream
        The stream object to write to; its 'write' method will be
        invoked.
    sourcemap_stream
        If one is provided, the sourcemap will be written out to it.
    sourcemap_normalize_mappings
        Flag for the normalization of the sourcemap mappings; Defaults
        to True to enable a reduction in output size.
    sourcemap_normalize_paths
        If set to true, all absolute paths will be converted to the
        relative form when the sourcemap is generated, if all paths
        provided are in the absolute form.

        Defaults to True to enable a reduction in output size.
    """

    # TODO if there is a custom instance of bookkeeping class,
    # check that multiple input nodes from different source files
    # can be merged into one.
    mappings, sources, names = sourcemap.write(
        unparser(node), output_stream, normalize=sourcemap_normalize_mappings)
    if sourcemap_stream:
        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream,
            normalize_paths=sourcemap_normalize_paths,
        )
