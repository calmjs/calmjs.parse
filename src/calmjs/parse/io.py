# -*- coding: utf-8 -*-
"""
Generic io functions for use with parsers.
"""

from itertools import chain
from collections import Iterable
from calmjs.parse.asttypes import Node
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
        unparser, nodes, output_stream, sourcemap_stream=None,
        sourcemap_normalize_mappings=True,
        sourcemap_normalize_paths=True,
        source_mapping_url=NotImplemented):
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
    nodes
        The Node or list of Nodes to stream to the output stream with
        the unparser.
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
    source_mapping_url
        If unspecified, the default derived path will be written as a
        sourceMappingURL comment into the output stream.  If explicitly
        specified with a value, that will be written instead.  Set to
        None to disable this.
    """

    chunks = None
    if isinstance(nodes, Node):
        chunks = unparser(nodes)
    elif isinstance(nodes, Iterable):
        raw = [unparser(node) for node in nodes if isinstance(node, Node)]
        if raw:
            chunks = chain(*raw)

    if not chunks:
        raise TypeError('must either provide a Node or list containing Nodes')

    mappings, sources, names = sourcemap.write(
        chunks, output_stream, normalize=sourcemap_normalize_mappings)
    if sourcemap_stream:
        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream,
            normalize_paths=sourcemap_normalize_paths,
            source_mapping_url=source_mapping_url,
        )
