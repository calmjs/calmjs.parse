# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import base64
import json
from io import StringIO
from os.path import join
from tempfile import mktemp

from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.asttypes import Node
from calmjs.parse.ruletypes import Attr
from calmjs.parse.ruletypes import Text
from calmjs.parse.unparsers.base import BaseUnparser
from calmjs.parse import io


class IOTestCase(unittest.TestCase):

    def test_read(self):
        # given that there is no generic parser, emulate one like so
        def parser(text):
            result = Node()
            result.raw = text
            return result

        stream = StringIO('var foo = "bar";')
        node = io.read(parser, stream)
        self.assertIsNone(node.sourcepath)

        stream.name = 'somefile.js'
        node = io.read(parser, stream)
        self.assertEqual(node.sourcepath, 'somefile.js')

    def test_read_callable(self):
        # given that there is no generic parser, emulate one like so
        def parser(text):
            result = Node()
            result.raw = text
            return result

        stream = StringIO('var foo = "bar";')

        def close():
            stream._closed = True

        def wrapper():
            stream.close = close
            return stream

        stream = StringIO('var foo = "bar";')
        io.read(parser, wrapper)
        self.assertTrue(stream._closed)

    def test_read_error(self):
        # given that there is no generic parser, emulate one like so
        def parser(text):
            raise ECMASyntaxError('Illegal input')

        def not_a_parser(text):
            raise Exception('Illegal input')

        stream = StringIO('var foo = "bar";')
        stream.name = 'somefile.js'
        with self.assertRaises(Exception) as e:
            io.read(parser, stream)

        self.assertEqual("Illegal input in 'somefile.js'", e.exception.args[0])

        stream = StringIO('var foo = "bar";')
        with self.assertRaises(Exception) as e:
            io.read(not_a_parser, stream)

        self.assertNotEqual(
            "Illegal input in 'somefile.js'", e.exception.args[0])

    def test_write_no_sourcemap(self):
        root = mktemp()
        definitions = {'Node': (
            Attr(attr='left'), Attr(attr='op'), Attr(attr='right'),)}

        # the program node; attributes are assigned to mimic a real one
        program = Node()
        program.left, program.op, program.right = ('foo', '=', 'true')
        program.sourcepath = join(root, 'original.js')
        program._token_map = {
            'foo': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'true': [(6, 1, 7)],
        }

        output_stream = StringIO()
        output_stream.name = join(root, 'processed.js')

        unparser = BaseUnparser(definitions)
        io.write(unparser, program, output_stream)
        self.assertEqual('foo=true', output_stream.getvalue())

    def test_write_sourcemap(self):
        root = mktemp()
        definitions = {'Node': (
            Attr(attr='left'), Attr(attr='op'), Attr(attr='right'),)}

        # the program node; attributes are assigned to mimic a real one
        program = Node()
        program.left, program.op, program.right = ('foo', '=', 'true')
        program.sourcepath = join(root, 'original.js')
        program._token_map = {
            'foo': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'true': [(6, 1, 7)],
        }

        # streams
        output_stream = StringIO()
        output_stream.name = join(root, 'processed.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'processed.js.map')

        unparser = BaseUnparser(definitions)
        io.write(unparser, program, output_stream, sourcemap_stream)

        sourcemap = json.loads(sourcemap_stream.getvalue())
        self.assertEqual({
            "version": 3,
            "sources": ["original.js"],
            "names": [],
            "mappings": "AAAA,GAAI,CAAE",
            "file": "processed.js"
        }, sourcemap)
        self.assertEqual(
            'foo=true\n//# sourceMappingURL=processed.js.map\n',
            output_stream.getvalue())

    def test_write_sourcemap_omitted(self):
        root = mktemp()
        definitions = {'Node': (
            Attr(attr='left'), Attr(attr='op'), Attr(attr='right'),)}

        # the program node; attributes are assigned to mimic a real one
        program = Node()
        program.left, program.op, program.right = ('foo', '=', 'true')
        program.sourcepath = join(root, 'original.js')
        program._token_map = {
            'foo': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'true': [(6, 1, 7)],
        }

        # streams
        output_stream = StringIO()
        output_stream.name = join(root, 'processed.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'processed.js.map')

        unparser = BaseUnparser(definitions)
        io.write(
            unparser, program, output_stream, sourcemap_stream,
            source_mapping_url=None)

        sourcemap = json.loads(sourcemap_stream.getvalue())
        self.assertEqual({
            "version": 3,
            "sources": ["original.js"],
            "names": [],
            "mappings": "AAAA,GAAI,CAAE",
            "file": "processed.js"
        }, sourcemap)
        self.assertEqual(
            'foo=true',
            output_stream.getvalue())

    def test_write_multiple(self):
        root = mktemp()
        definitions = {'Node': (
            Attr(attr='left'), Text(value=' '),
            Attr(attr='op'), Text(value=' '),
            Attr(attr='right'), Text(value=';'),
        )}

        # the program node; attributes are assigned to mimic a real one
        program1 = Node()
        program1.left, program1.op, program1.right = ('foo', '=', 'true')
        program1.sourcepath = join(root, 'program1.js')
        program1._token_map = {
            'foo': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'true': [(6, 1, 7)],
        }
        program2 = Node()
        program2.left, program2.op, program2.right = ('bar', '=', 'false')
        program2.sourcepath = join(root, 'program2.js')
        program2._token_map = {
            'bar': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'false': [(6, 1, 7)],
        }

        # streams
        output_stream = StringIO()
        output_stream.name = join(root, 'packed.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'packed.js.map')

        unparser = BaseUnparser(definitions)
        io.write(
            unparser, [program1, program2], output_stream, sourcemap_stream,
            source_mapping_url=None)

        self.assertEqual('foo = true;bar = false;', output_stream.getvalue())

        sourcemap = json.loads(sourcemap_stream.getvalue())
        self.assertEqual({
            "version": 3,
            "sources": ["program1.js", "program2.js"],
            "names": [],
            "mappings": "AAAA,WCAA",
            "file": "packed.js"
        }, sourcemap)

    def test_write_callables(self):
        closed = []

        class Stream(StringIO):
            # don't actually close the stream so it can be read later by
            # the tests
            def close(self):
                closed.append(self)

        # streams
        root = mktemp()
        output_stream = Stream()
        output_stream.name = join(root, 'packed.js')
        sourcemap_stream = Stream()
        sourcemap_stream.name = join(root, 'packed.js.map')

        def f_output_stream():
            return output_stream

        def f_sourcemap_stream():
            return sourcemap_stream

        definitions = {'Node': (
            Attr(attr='left'), Text(value=' '),
            Attr(attr='op'), Text(value=' '),
            Attr(attr='right'), Text(value=';'),
        )}

        # the program node; attributes are assigned to mimic a real one
        program1 = Node()
        program1.left, program1.op, program1.right = ('foo', '=', 'true')
        program1.sourcepath = join(root, 'program1.js')
        program1._token_map = {
            'foo': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'true': [(6, 1, 7)],
        }
        program2 = Node()
        program2.left, program2.op, program2.right = ('bar', '=', 'false')
        program2.sourcepath = join(root, 'program2.js')
        program2._token_map = {
            'bar': [(0, 1, 1)],
            '=': [(4, 1, 5)],
            'false': [(6, 1, 7)],
        }

        unparser = BaseUnparser(definitions)
        io.write(
            unparser, [program1, program2],
            f_output_stream, f_sourcemap_stream,
            source_mapping_url=None)

        self.assertIn(output_stream, closed)
        self.assertIn(sourcemap_stream, closed)
        self.assertEqual('foo = true;bar = false;', output_stream.getvalue())

        sourcemap = json.loads(sourcemap_stream.getvalue())
        self.assertEqual({
            "version": 3,
            "sources": ["program1.js", "program2.js"],
            "names": [],
            "mappings": "AAAA,WCAA",
            "file": "packed.js"
        }, sourcemap)

    def test_write_same_stream_callable(self):
        # streams
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'packed.js')
        called = []
        closed = []

        def close():
            closed.append(True)

        output_stream.close = close

        def f_output_stream():
            called.append(True)
            return output_stream

        definitions = {'Node': (
            Attr(attr='text'), Text(value=';'),
        )}

        # the program node; attributes are assigned to mimic a real one
        program = Node()
        program.text = 'hello'
        program.sourcepath = join(root, 'program.js')
        program._token_map = {'hello': [(0, 1, 1)]}

        unparser = BaseUnparser(definitions)
        io.write(unparser, [program], f_output_stream, f_output_stream)

        self.assertEqual(1, len(called))
        self.assertEqual(1, len(closed))
        output = output_stream.getvalue()
        self.assertIn('hello', output)
        self.assertNotIn('program.js', output)
        # since output stream is a StringIO, default to utf8 encoding
        self.assertIn('data:application/json;base64;charset=utf8', output)
        # decode the base64 string
        self.assertEqual({
            "version": 3,
            "sources": ["program.js"],
            "names": [],
            "mappings": "AAAA",
            "file": "packed.js"
        }, json.loads(base64.b64decode(
            output.splitlines()[-1].split(',')[-1].encode('utf8')
        ).decode('utf8')))

    def test_write_error_handled_callable_closed(self):
        # streams
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'packed.js')
        closed = []

        def close():
            closed.append(True)

        output_stream.close = close

        def f_output_stream():
            return output_stream

        def f_error():
            raise IOError('some error happened')

        definitions = {'Node': (
            Attr(attr='text'), Text(value=';'),
        )}

        # the program node; attributes are assigned to mimic a real one
        program = Node()
        program.text = 'hello'
        program.sourcepath = join(root, 'program.js')
        program._token_map = {'hello': [(0, 1, 1)]}

        unparser = BaseUnparser(definitions)
        with self.assertRaises(IOError):
            io.write(unparser, [program], f_output_stream, f_error)

        self.assertEqual(1, len(closed))
        self.assertEqual('hello;', output_stream.getvalue())
        self.assertNotIn('program.js', output_stream.getvalue())

    def test_write_wrong_type(self):
        stream = StringIO()
        unparser = BaseUnparser({})
        with self.assertRaises(TypeError):
            io.write(unparser, [], stream)

        with self.assertRaises(TypeError):
            io.write(unparser, '', stream)
