# -*- coding: utf-8 -*-
"""
Generic io functions for use with parsers.
"""

from itertools import chain
try:
    from collections.abc import Iterable
except ImportError:  # pragma: no cover
    from collections import Iterable
from calmjs.parse.asttypes import Node
from calmjs.parse import sourcemap
from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.utils import repr_compat


def read(parser, stream):
    """
    Return an AST from the input ES5 stream.

    Arguments

    parser
        A parser instance.
    stream
        Either a stream object or a callable that produces one.  The
        stream object to read from; its 'read' method will be invoked.

        If a callable was provided, the 'close' method on its return
        value will be called to close the stream.
    """

    source = stream() if callable(stream) else stream
    try:
        text = source.read()
        stream_name = getattr(source, 'name', None)
        try:
            result = parser(text)
        except ECMASyntaxError as e:
            error_name = repr_compat(stream_name or source)
            raise type(e)('%s in %s' % (str(e), error_name))
    finally:
        if callable(stream):
            source.close()

    result.sourcepath = stream_name
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
        Either a stream object or a callable that produces one.  The
        stream object to write to; its 'write' method will be invoked.

        If a callable was provided, the 'close' method on its return
        value will be called to close the stream.
    sourcemap_stream
        If one is provided, the sourcemap will be written out to it.
        Like output_stream, it could also be a callable and be handled
        in the same manner.

        If this argument is the same as output_stream (note: the return
        value of any callables are not compared), the stream object that
        is the same as the output_stream will be used for writing out
        the source map, and the source map will instead be encoded as a
        'data:application/json;base64,' URL.
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

    closer = []

    def get_stream(stream):
        if callable(stream):
            result = stream()
            closer.append(result.close)
        else:
            result = stream
        return result

    def cleanup():
        for close in reversed(closer):
            close()

    chunks = None
    if isinstance(nodes, Node):
        chunks = unparser(nodes)
    elif isinstance(nodes, Iterable):
        raw = [unparser(node) for node in nodes if isinstance(node, Node)]
        if raw:
            chunks = chain(*raw)

    if not chunks:
        raise TypeError('must either provide a Node or list containing Nodes')

    try:
        out_s = get_stream(output_stream)
        sourcemap_stream = (
            out_s if sourcemap_stream is output_stream else sourcemap_stream)
        mappings, sources, names = sourcemap.write(
            chunks, out_s, normalize=sourcemap_normalize_mappings)
        if sourcemap_stream:
            sourcemap_stream = get_stream(sourcemap_stream)
            sourcemap.write_sourcemap(
                mappings, sources, names, out_s, sourcemap_stream,
                normalize_paths=sourcemap_normalize_paths,
                source_mapping_url=source_mapping_url,
            )
    finally:
        cleanup()
