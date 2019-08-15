# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import base64
import codecs
import json
import logging
import textwrap
from os.path import join
from io import StringIO
from io import BytesIO
from tempfile import mktemp

from calmjs.parse import sourcemap
from calmjs.parse.testing.util import setup_logger


class NameTestCase(unittest.TestCase):

    def test_name_update(self):
        names = sourcemap.Names()
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('world'), 1)
        self.assertEqual(names.update('world'), 0)
        self.assertEqual(names.update('hello'), -1)
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('goodbye'), 2)
        self.assertEqual(names.update('hello'), -2)
        self.assertEqual(names.update('goodbye'), 2)
        self.assertEqual(names.update('goodbye'), 0)
        self.assertEqual(names.update('goodbye'), 0)
        self.assertEqual(names.update('goodbye'), 0)
        self.assertEqual(names.update('world'), -1)
        self.assertEqual(names.update('person'), 2)
        self.assertEqual(names.update('people'), 1)
        self.assertEqual(names.update('people'), 0)
        self.assertEqual(names.update('hello'), -4)

        self.assertEqual(
            list(names), ['hello', 'world', 'goodbye', 'person', 'people'])

    def test_null(self):
        names = sourcemap.Names()
        self.assertIs(names.update(None), None)
        self.assertEqual(list(names), [])
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('hello'), 0)
        self.assertIs(names.update(None), None)
        self.assertEqual(names.update('goodbye'), 1)
        self.assertEqual(names.update('goodbye'), 0)

    def test_not_implemented(self):
        names = sourcemap.Names()
        self.assertEqual(names.update(NotImplemented), 0)
        self.assertEqual(list(names), [NotImplemented])


class BookkeeperTestCase(unittest.TestCase):

    def test_empty(self):
        book = sourcemap.Bookkeeper()
        with self.assertRaises(AttributeError) as e:
            book.foo
        self.assertEqual(
            e.exception.args[0], "'Bookkeeper' object has no attribute 'foo'")

        with self.assertRaises(AttributeError) as e:
            del book.foo

    def test_typecheck(self):
        book = sourcemap.Bookkeeper()
        with self.assertRaises(TypeError) as e:
            book.foo = 'notanint'
        self.assertEqual(
            e.exception.args[0], "assignment must be of type 'int'")

    def test_usage(self):
        book = sourcemap.Bookkeeper()
        book.foo = 123
        self.assertEqual(book.foo, 0)
        self.assertEqual(book.foo, 0)
        self.assertEqual(book._foo, 123)
        book.foo = 124
        self.assertEqual(book.foo, 1)
        self.assertEqual(book.foo, 1)
        self.assertEqual(book._foo, 124)
        book.foo = 1
        self.assertEqual(book.foo, -123)
        self.assertEqual(book.foo, -123)
        self.assertEqual(book._foo, 1)
        book.foo = 1
        self.assertEqual(book.foo, 0)
        self.assertEqual(book.foo, 0)
        self.assertEqual(book._foo, 1)
        book.foo = 1
        self.assertEqual(book.foo, 0)
        self.assertEqual(book.foo, 0)
        self.assertEqual(book._foo, 1)
        book.foo = 2
        book.foo = 2
        self.assertEqual(book.foo, 0)
        self.assertEqual(book._foo, 2)

    def test_private_reset(self):
        book = sourcemap.Bookkeeper()
        book.foo = 123
        book.foo = 124
        self.assertEqual(book.foo, 1)
        book._foo = 1
        self.assertEqual(book.foo, 0)
        self.assertEqual(book._foo, 1)
        book._foo = 124
        self.assertEqual(book.foo, 0)
        self.assertEqual(book._foo, 124)

    def test_del_reset(self):
        book = sourcemap.Bookkeeper()
        book.foo = 123
        book.foo = 124
        self.assertEqual(book.foo, 1)
        del book.foo
        self.assertEqual(book.foo, 0)

    def test_default_book(self):
        book = sourcemap.default_book()
        self.assertEqual(book.keeper.sink_column, 0)
        self.assertEqual(book.keeper.source_line, 0)
        self.assertEqual(book.keeper.source_column, 0)
        book.keeper.sink_sink_column = 0
        book.keeper.source_line = 1
        book.keeper.source_column = 1
        self.assertEqual(book.keeper.sink_column, 0)
        self.assertEqual(book.keeper.source_line, 0)
        self.assertEqual(book.keeper.source_column, 0)


class NormalizeRunningTestCase(unittest.TestCase):

    def test_empty(self):
        remapped, column = sourcemap.normalize_mapping_line([])
        self.assertEqual([], remapped)
        self.assertEqual(0, column)
        remapped, column = sourcemap.normalize_mapping_line([()])
        # that nonsensical empty element should be dropped
        self.assertEqual([], remapped)
        self.assertEqual(0, column)

        # ensure that previous column also returned
        remapped, column = sourcemap.normalize_mapping_line([], 4)
        self.assertEqual([], remapped)
        self.assertEqual(4, column)

    def test_single_elements_only(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0,),
            (4,),
        ])
        # leading elements are simply not going to be recorded
        self.assertEqual([], remapped)
        self.assertEqual(0, column)

    def test_leading_single_elements(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0,),
            (4,),
            (4,),
            (0, 0, 0, 0),
        ])
        # they would be merged down to the actual real node, since there
        # was nothing to stop.
        self.assertEqual([(8, 0, 0, 0)], remapped)
        self.assertEqual(0, column)

    def test_trailing_single_elements(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0,),
            (4,),
            (4,),
            (0, 0, 0, 0),
            (4,),
            (4,),
            (4,),
        ])
        # the first trailing node would be kept, remaining are discarded
        self.assertEqual([(8, 0, 0, 0), (4,)], remapped)
        self.assertEqual(0, column)

    def test_interspersed_single_elements(self):
        # example how this might look:
        # source
        #     XXXX(YYYZZZ)
        # sink (? marks ignored)
        #     ????????XXXX????(YYYZZZ)??????????
        remapped, column = sourcemap.normalize_mapping_line([
            (4,),
            (4,),
            # symbol runs for 4 characters
            (0, 0, 0, 0),
            (4,),
            # next two symbols run for a total of 8 characters, after
            # another 4 column gap.
            (4, 0, 0, 4),
            (4, 0, 0, 4),
            (4,),
        ])
        self.assertEqual([(8, 0, 0, 0), (4,), (4, 0, 0, 4), (8,)], remapped)
        self.assertEqual(4, column)

    def test_unmodified(self):
        # this is a typical canonical example
        # console.log("hello world");
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (7, 0, 0, 7),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
        ])
        self.assertEqual([(0, 0, 0, 0)], remapped)
        self.assertEqual(26, column)

    def test_unmodified_offsetted(self):
        # simulate the removal of indentation
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 2),
            (7, 0, 0, 7),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
        ])
        self.assertEqual([(0, 0, 0, 2)], remapped)
        self.assertEqual(26, column)

    def test_five_segment(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (7, 0, 0, 7, 0),
            (1, 0, 0, 1),
            (3, 0, 0, 3, 1),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
            (3, 0, 0, 3, 1),
        ])
        self.assertEqual([
            (0, 0, 0, 0),
            (7, 0, 0, 7, 0),
            (1, 0, 0, 1),
            (3, 0, 0, 3, 1),
            (1, 0, 0, 1),
            (17, 0, 0, 17, 1),  # this finally got collapsed
        ], remapped)
        self.assertEqual(0, column)

    def test_file_changed(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (7, 0, 0, 7),
            (1, 0, 0, 1),
            (1, 1, 0, 1),
            (1, 0, 0, 1),
            (1, -1, 0, 1),
            (1, 0, 0, 1),
        ])
        self.assertEqual([
            (0, 0, 0, 0),
            (9, 1, 0, 9),
            (2, -1, 0, 2),
        ], remapped)
        self.assertEqual(1, column)

    def test_line_changed(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (7, 0, 0, 7),
            (1, 0, 0, 1),
            (0, 0, 1, 0),
            (1, 0, 0, 1),
            (17, 0, 0, 17),
            (1, 0, 0, 1),
            (0, 0, 1, 0),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
            (1, 0, 0, 1),
        ])
        self.assertEqual([
            (0, 0, 0, 0),
            (8, 0, 1, 8),
            (19, 0, 1, 19),
        ], remapped)
        self.assertEqual(5, column)

    def test_column_offset(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (1, 0, 0, 7),
            (1, 0, 0, 1),
            (1, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
        ])
        self.assertEqual([
            (0, 0, 0, 0),
            (1, 0, 0, 7),
            (2, 0, 0, 4),
        ], remapped)
        self.assertEqual(15, column)

    def test_with_previous_source(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (1, 0, 0, 7),
            (1, 0, 0, 1),
            (1, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
        ], 4)
        self.assertEqual([
            (0, 0, 0, 4),
            (1, 0, 0, 7),
            (2, 0, 0, 4),
        ], remapped)
        self.assertEqual(15, column)

    def test_negative_offset(self):
        remapped, column = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (1, 0, 0, 7),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
            (1, 0, 0, -26),
            (1, 0, 0, 7),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
        ])
        self.assertEqual([
            (0, 0, 0, 0),
            (1, 0, 0, 7),
            (20, 0, 0, -7),
            (1, 0, 0, 7),
        ], remapped)


class SourceMapTestCase(unittest.TestCase):

    def test_source_map_basic(self):
        stream = StringIO()

        fragments = [
            ('console', 1, 1, None, 'demo.js'),
            ('.', 1, 8, None, 'demo.js'),
            ('log', 1, 9, None, 'demo.js'),
            ('(', 1, 12, None, 'demo.js'),
            ('"hello world"', 1, 13, None, 'demo.js'),
            (')', 1, 26, None, 'demo.js'),
            (';', 1, 27, None, 'demo.js'),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(sources, ['demo.js'])
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_source_map_inferred(self):
        stream = StringIO()

        # Note the 0 values, as that signifies inferred elements for the
        # row/col, and then None for source will be replaced with an
        # 'about:invalid' source.
        fragments = [
            ('console', 1, 1, None, None),
            ('.', 1, 8, None, None),
            ('log', 1, 9, None, None),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', 0, 0, None, None),
            (';', 0, 0, None, None),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(sources, ['about:invalid'])
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_source_map_source_not_implemented(self):
        stream = StringIO()

        fragments = [
            ('console', 1, 1, None, NotImplemented),
            ('.', 1, 8, None, None),
            ('log', 1, 9, None, None),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', 0, 0, None, None),
            (';', 0, 0, None, None),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(sources, ['about:invalid'])
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_source_map_source_none_then_not_implemented_then_named(self):
        stream = StringIO()

        fragments = [
            ('console', 1, 1, None, None),
            ('.', 1, 8, None, NotImplemented),
            ('log', 1, 9, None, 'named.js'),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', 0, 0, None, None),
            (';', 0, 0, None, NotImplemented),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(sources, ['about:invalid', 'named.js'])
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            # the first None implied value converted to invalid, then
            # the named.js bumps it up 1, then backtracked back to 0 at
            # the end.
            # Yes, the example is a bit contrived, due to how the
            # positions are interweaved between the two files.
            [(0, 0, 0, 0), (8, 1, 0, 8), (18, -1, 0, 18)],
        ])

    def test_source_map_inferred_row_offset(self):
        stream = StringIO()

        # Note that the first row is 3.
        fragments = [
            ('var', 3, 1, None, None),
            (' ', 0, 0, None, None),
            ('main', 3, 5, None, None),
            (';', 0, 0, None, None),
        ]

        mapping, sources, names = sourcemap.write(
            fragments, stream, normalize=False)
        self.assertEqual(stream.getvalue(), 'var main;')
        self.assertEqual(names, [])
        self.assertEqual(sources, ['about:invalid'])
        self.assertEqual(mapping, [
            [(0, 0, 2, 0), (3, 0, 0, 3), (1, 0, 0, 1), (4, 0, 0, 4)],
        ])

    def test_source_map_known_standard_newline(self):
        # for cases where pretty printing happened
        # e.g. (function() { console.log("hello world"); })()
        # with all values known.
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        fragments = [
            ('(', 1, 1, None, None),
            ('function', 1, 2, None, None),
            ('(', 1, 10, None, None),
            (') ', 1, 11, None, None),
            ('{\n', 1, 13, None, None),
            # may be another special case here, to normalize the _first_
            # fragment
            ('  ', None, None, None, None),
            ('console', 1, 15, None, None),
            ('.', 1, 22, None, None),
            ('log', 1, 23, None, None),
            ('(', 1, 26, None, None),
            ('"hello world"', 1, 27, None, None),
            (')', 1, 40, None, None),
            (';\n', 1, 41, None, None),
            ('}', 1, 43, None, None),
            (')', 1, 44, None, None),
            ('(', 1, 45, None, None),
            (')', 1, 46, None, None),
            (';', 1, 47, None, None),
        ]
        mapping, _, names = sourcemap.write(fragments, stream, normalize=False)
        self.assertEqual(stream.getvalue(), textwrap.dedent("""
        (function() {
          console.log("hello world");
        })();
        """).strip())
        self.assertEqual(names, [])
        self.assertEqual([[
            (0, 0, 0, 0), (1, 0, 0, 1), (8, 0, 0, 8), (1, 0, 0, 1),
            (2, 0, 0, 2)
        ], [
            (0,), (2, 0, 0, 2), (7, 0, 0, 7), (1, 0, 0, 1), (3, 0, 0, 3),
            (1, 0, 0, 1), (13, 0, 0, 13), (1, 0, 0, 1)
        ], [
            (0, 0, 0, 2), (1, 0, 0, 1), (1, 0, 0, 1), (1, 0, 0, 1),
            (1, 0, 0, 1)
        ]], mapping)
        self.assertNotIn("WARNING", err.getvalue())
        # the normalized version should also have the correct offsets
        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(
            [[(0, 0, 0, 0)], [(2, 0, 0, 14)], [(0, 0, 0, 28)]], mapping)

    def test_source_map_inferred_standard_newline(self):
        # for cases where pretty printing happened
        # e.g. (function() { console.log("hello world"); })()
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        fragments = [
            ('(', 1, 1, None, None),
            ('function', 1, 2, None, None),
            ('(', 1, 10, None, None),
            (') ', 1, 11, None, None),
            ('{\n', 1, 13, None, None),
            # may be another special case here, to normalize the _first_
            # fragment
            ('  ', None, None, None, None),
            ('console', 1, 15, None, 'demo.js'),
            ('.', 1, 22, None, None),
            ('log', 1, 23, None, None),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 27, None, None),
            (')', 0, 0, None, None),
            (';\n', 0, 0, None, None),
            # note that the AST will need to record/provide the ending
            # value to this if the usage on a newline is to be supported
            # like so, otherwise all unmarked symbols will be clobbered
            # in an indeterminate manner, given that there could be
            # arbitrary amount of white spaces before the following
            # ending characters in the original source text.
            # In other words, if '}' is not tagged with (1,43), (or the
            # position that it was from, the generated source map will
            # guaranteed to be wrong as the starting column cannot be
            # correctly inferred without the original text.
            ('}', 1, 43, None, None),  # this one cannot be inferred.
            (')', 0, 0, None, None),   # this one can be.
            ('(', 1, 45, None, None),  # next starting symbol
            (')', 1, 46, None, None),
            (';', 0, 0, None, None),
        ]
        mapping, _, names = sourcemap.write(fragments, stream, normalize=False)
        self.assertEqual(stream.getvalue(), textwrap.dedent("""
        (function() {
          console.log("hello world");
        })();
        """).strip())
        self.assertEqual(names, [])
        self.assertEqual([[
            (0, 0, 0, 0), (1, 0, 0, 1), (8, 0, 0, 8), (1, 0, 0, 1),
            (2, 0, 0, 2)
        ], [
            (0,), (2, 0, 0, 2), (7, 0, 0, 7), (1, 0, 0, 1), (3, 0, 0, 3),
            (1, 0, 0, 1), (13, 0, 0, 13), (1, 0, 0, 1)
        ], [
            (0, 0, 0, 2), (1, 0, 0, 1), (1, 0, 0, 1), (1, 0, 0, 1),
            (1, 0, 0, 1)
        ]], mapping)
        self.assertNotIn("WARNING", err.getvalue())
        # the normalized version should also have the correct offsets
        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(
            [[(0, 0, 0, 0)], [(2, 0, 0, 14)], [(0, 0, 0, 28)]], mapping)
        self.assertEqual(sources, ['demo.js'])

    def test_source_map_inferred_trailing_newline_calculated(self):
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        # Note the None values, as that signifies inferred elements.
        fragments = [
            ('console.log(\n  "hello world");', 1, 1, None, None),
        ]
        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log(\n  "hello world");')
        self.assertEqual(names, [])
        self.assertEqual([
            [(0, 0, 0, 0)],
            [(0, 0, 1, 0)],
        ], mapping)
        self.assertNotIn("WARNING", err.getvalue())

    def test_source_map_inferred_trailing_newline_unknown(self):
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        # Note the None values, as that signifies inferred elements.
        fragments = [
            ('console.log(\n  "hello world");', 1, 1, None, None),
            ('/* foo\nbar */', 0, 0, None, None),
            (' /* foo\nbar */', None, None, None, 'some_script.js'),
        ]
        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(
            stream.getvalue(),
            'console.log(\n  "hello world");/* foo\nbar */ /* foo\nbar */',
        )
        self.assertEqual(names, [])
        self.assertEqual([
            [(0, 0, 0, 0)],
            [(0, 0, 1, 0)],
            # yeah the comments really came out wrong it looks like
            [(0, 0, 0, 17), (6,)],
            [],
        ], mapping)
        self.assertIn(
            "WARNING text in the generated stream at line 3 may be mapped "
            "incorrectly due to stream fragment containing a trailing newline "
            "character provided without both lineno and colno defined; "
            "text fragment originated from: <unknown>",
            err.getvalue()
        )
        self.assertIn(
            "WARNING text in the generated stream at line 4 may be mapped "
            "incorrectly due to stream fragment containing a trailing newline "
            "character provided without both lineno and colno defined; "
            "text fragment originated from: some_script.js",
            err.getvalue()
        )

    def test_source_map_renamed(self):
        stream = StringIO()

        fragments = [
            ('a', 1, 1, 'console', None),
            ('.', 1, 8, None, None),
            ('b', 1, 9, 'log', None),
            ('(', 1, 12, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', 1, 26, None, None),
            (';', 1, 27, None, None),
        ]

        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'a.b("hello world");')
        self.assertEqual(names, ['console', 'log'])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 1, 1), (1, 0, 0, 3)]
        ])

    def test_source_map_wrongly_inferred_initial_indents(self):
        # it should still be able to correct it
        # this is why indentation should simply be omitted and replace
        # both the line/col counter to None
        stream = StringIO()
        fragments = [
            (' ', 0, 0, None, None),  # was two spaces, now single space.
            (' ', 0, 0, None, None),
            ('console', 1, 5, None, None),
            ('.', 1, 12, None, None),
            ('log', 1, 13, None, None),
            ('(', 0, 0, None, None),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 18, None, None),
            (')', 0, 0, None, None),
            (')', 0, 0, None, None),
            (';', 0, 0, None, None),
        ]

        mapping, _, names = sourcemap.write(fragments, stream, normalize=False)
        self.assertEqual(stream.getvalue(), '  console.log(("hello world"));')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [[
            (0, 0, 0, 0), (1, 0, 0, 1),
            (1, 0, 0, 3), (7, 0, 0, 7), (1, 0, 0, 1), (3, 0, 0, 3),
            (1, 0, 0, 1), (1, 0, 0, 1), (13, 0, 0, 13), (1, 0, 0, 1),
            (1, 0, 0, 1),
        ]])

        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(mapping, [
            [(0, 0, 0, 0), (2, 0, 0, 4)],
        ])

    def test_source_map_unmapped_initial_indent(self):
        stream = StringIO()

        fragments = [
            ('  ', None, None, None, None),
            ('console', 1, 1, None, None),
            ('.', 1, 8, None, None),
            ('log', 1, 9, None, None),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', 0, 0, None, None),
            (';', 0, 0, None, None),
        ]

        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), '  console.log("hello world");')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(2, 0, 0, 0)],
        ])

    def test_source_map_mapped_initial_indent(self):
        stream = StringIO()

        fragments = [
            ('  ', 1, 1, None, None),
            ('console', 1, 3, None, None),
            ('.', 1, 10, None, None),
            ('log', 1, 11, None, None),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 15, None, None),
            (')', 0, 0, None, None),
            (';', 0, 0, None, None),
        ]

        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), '  console.log("hello world");')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_donottrack_names_source_of_dropped(self):
        stream = StringIO()

        fragments = [
            ('  ', None, None, '\t', 'original.py'),
            ('console', None, None, 'print', 'nowhere.js'),
            ('.', None, None, 'dot', 'somewhere.js'),
            ('log', 1, 1, 'print', 'original.py'),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 7, None, None),
            (')', 0, 0, None, None),
            (';', None, None, None, None),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), '  console.log("hello world");')
        self.assertEqual(names, ['print'])
        self.assertEqual(sources, ['original.py'])
        self.assertEqual(mapping, [
            [(10, 0, 0, 0, 0), (3, 0, 0, 5), (15,)],
        ])

    def test_track_shrunk_name(self):
        stream = StringIO()

        # 123456789012345678901234567
        # console.log("hello world");
        fragments = [
            ('print', 1, 1, 'console.log', 'original.js'),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', 0, 0, None, None),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'print("hello world")')
        self.assertEqual(names, ['console.log'])
        self.assertEqual(sources, ['original.js'])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0, 0), (5, 0, 0, 11)],
        ])

    def test_track_expanded_name(self):
        stream = StringIO()

        # 12345678901234567890
        # print("hello world")
        fragments = [
            ('console.log', 0, 0, 'print', 'original.py'),
            ('(', 0, 0, None, None),
            ('"hello world"', 1, 7, None, None),
            (')', 0, 0, None, None),
            (';', None, None, None, None),
        ]

        mapping, sources, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(names, ['print'])
        self.assertEqual(sources, ['original.py'])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0, 0), (11, 0, 0, 5), (15,)],
        ])

    def test_multiple_unmapped_chunks(self):
        stream = StringIO()

        fragments = [
            (' ', None, None, None, None),
            (' ', None, None, None, None),
            (' ', None, None, None, None),
            ('x', 1, 1, None, None),
            ('x', 1, 1, None, None),
            ('x', 1, 1, None, None),
            (' ', None, None, None, None),
            (' ', None, None, None, None),
            (' ', None, None, None, None),
            ('y', 1, 3, None, None),
            ('y', 1, 3, None, None),
            ('y', 1, 3, None, None),
        ]

        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), '   xxx   yyy')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [[
            (3, 0, 0, 0),
            (1, 0, 0, 0),
            (1, 0, 0, 0),
            (1,),
            (3, 0, 0, 2),
            (1, 0, 0, 0),
            (1, 0, 0, 0),
        ]])

    def test_source_map_remapped_symbols_without_original(self):
        # for cases where the program have been wrapped and transpiled
        # e.g. (function() { $program })()
        # using: console log "hello world"
        stream = StringIO()
        fragments = [
            ('(', None, None, None, None),
            ('function', None, None, None, None),
            ('(', None, None, None, None),
            (') ', None, None, None, None),
            ('{\n', None, None, None, None),
            # may be another special case here, to normalize the _first_
            # fragment
            ('  ', None, None, None, None),
            ('console', 1, 1, None, None),
            ('.', None, None, None, None),
            ('log', 1, 9, None, None),
            ('(', None, None, None, None),
            ('"hello world"', 1, 13, None, None),
            (')', None, None, None, None),
            (';', None, None, None, None),
            ('\n', None, None, None, None),
            ('}', None, None, None, None),
            (')', None, None, None, None),
            ('(', 0, None, None, None),  # testing for alternative conds.
            (')', None, 0, None, None),
            (';', None, None, None, None),
        ]
        mapping, _, names = sourcemap.write(fragments, stream, normalize=False)
        self.assertEqual(stream.getvalue(), textwrap.dedent("""
        (function() {
          console.log("hello world");
        })();
        """).strip())
        self.assertEqual(names, [])
        self.assertEqual([[
            (0,), (1,), (8,), (1,), (2,),
        ], [
            (0,),
            (2, 0, 0, 0), (7,), (1, 0, 0, 8), (3,), (1, 0, 0, 4), (13,),
            (1,), (1,),
        ], [
            (0,), (1,), (1,), (1,), (1,),
        ]], mapping)

        # the normalized version should also have the correct offsets
        mapping, _, names = sourcemap.write(fragments, stream)
        self.assertEqual([[], [
            (2, 0, 0, 0), (7,), (1, 0, 0, 8), (3,), (1, 0, 0, 4), (13,),
        ], []], mapping)

    def test_multiple_call(self):
        stream = StringIO()

        fragments1 = [
            ('a', 1, 1, 'console', 'demo1.js'),
            ('.', 1, 8, None, 'demo1.js'),
            ('log', 1, 9, None, 'demo1.js'),
            ('(', 1, 12, None, 'demo1.js'),
            ('"hello world"', 1, 13, None, 'demo1.js'),
            (')', 1, 26, None, 'demo1.js'),
            (';', 1, 27, None, 'demo1.js'),
        ]

        fragments2 = [
            ('a', 1, 1, 'console', 'demo2.js'),
            ('.', 1, 8, None, 'demo2.js'),
            ('log', 1, 9, None, 'demo2.js'),
            ('(', 1, 12, None, 'demo2.js'),
            ('"hello world"', 1, 13, None, 'demo2.js'),
            (')', 1, 26, None, 'demo2.js'),
            (';', 1, 27, None, 'demo2.js'),
        ]

        book = sourcemap.default_book()
        sources = sourcemap.Names()
        names = sourcemap.Names()

        mappings, _, _ = sourcemap.write(
            fragments1, stream, book=book, sources=sources, names=names,
            # Note that normalization is NOT supported until the last
            # step.
            normalize=False,
        )
        mappings, sources, namelist = sourcemap.write(
            fragments2, stream, book=book, sources=sources, names=names,
            mappings=mappings)

        self.assertEqual(
            stream.getvalue(), 'a.log("hello world");a.log("hello world");')
        self.assertEqual(namelist, ['console'])
        self.assertEqual(sources, ['demo1.js', 'demo2.js'])
        self.assertEqual(mappings, [
            [(0, 0, 0, 0, 0), (1, 0, 0, 7), (20, 1, 0, -7, 0), (1, 0, 0, 7)],
        ])

    def test_encode_sourcemap(self):
        sm = sourcemap.encode_sourcemap(
            'hello.min.js', [
                [(0, 0, 0, 0,), (6, 0, 0, 6,), (6, 0, 0, 6,)],
                []
            ], ['hello.js'], [],
        )
        self.assertEqual(sm, {
            "version": 3,
            "sources": ["hello.js"],
            "names": [],
            "mappings": "AAAA,MAAM,MAAM;",
            "file": "hello.min.js"
        })

    def test_write_sourcemap_standard(self):
        logs = setup_logger(self, sourcemap.logger, logging.WARNING)
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'srcfinal.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'srcfinal.js.map')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [join(root, 'src1.js'), join(root, 'src2.js')]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream)

        self.assertEqual({
            "version": 3,
            "sources": ["src1.js", "src2.js"],
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": "srcfinal.js"
        }, json.loads(sourcemap_stream.getvalue()))
        self.assertEqual(
            '\n//# sourceMappingURL=srcfinal.js.map\n',
            output_stream.getvalue())

        # ensure no warnings have been logged
        self.assertEqual('', logs.getvalue())

    def test_write_sourcemap_various_issues(self):
        logs = setup_logger(self, sourcemap.logger, logging.WARNING)
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'build', 'srcfinal.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'maps', 'srcfinal.js.map')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [
            join(root, 'src', 'src1.js'), 'hmm/src2.js',
            sourcemap.INVALID_SOURCE]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream)

        self.assertEqual({
            "version": 3,
            "sources": ["../src/src1.js", "hmm/src2.js", 'about:invalid'],
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": "../build/srcfinal.js",
        }, json.loads(sourcemap_stream.getvalue()))
        self.assertEqual(
            '\n//# sourceMappingURL=../maps/srcfinal.js.map\n',
            output_stream.getvalue())

        # warning about the about:invalid token is applied.
        self.assertIn(
            "sourcemap.sources[2] is either undefine or invalid - "
            "it is replaced with 'about:invalid'", logs.getvalue())

    def test_write_sourcemap_no_paths(self):
        logs = setup_logger(self, sourcemap.logger, logging.WARNING)
        output_stream = StringIO()
        sourcemap_stream = StringIO()
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [sourcemap.INVALID_SOURCE]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream)

        self.assertEqual({
            "version": 3,
            "sources": ['about:invalid'],
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": "about:invalid",
        }, json.loads(sourcemap_stream.getvalue()))
        self.assertEqual(
            '\n//# sourceMappingURL=about:invalid\n',
            output_stream.getvalue())

        # warnings about the about:invalid.
        self.assertIn(
            "sourcemap.file is either undefine or invalid - "
            "it is replaced with 'about:invalid'", logs.getvalue())
        self.assertIn(
            "sourcemap.sources[0] is either undefine or invalid - "
            "it is replaced with 'about:invalid'", logs.getvalue())
        self.assertIn(
            "sourceMappingURL is either undefine or invalid - "
            "it is replaced with 'about:invalid'", logs.getvalue())

    def test_write_sourcemap_no_normalize(self):
        logs = setup_logger(self, sourcemap.logger, logging.WARNING)
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'srcfinal.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'srcfinal.js.map')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [join(root, 'src1.js'), join(root, 'src2.js')]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream,
            normalize_paths=False)

        self.assertEqual({
            "version": 3,
            "sources": sources,
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": output_stream.name,
        }, json.loads(sourcemap_stream.getvalue()))
        self.assertEqual(
            '\n//# sourceMappingURL=%s\n' % sourcemap_stream.name,
            output_stream.getvalue())

        # ensure no warnings have been logged
        self.assertEqual('', logs.getvalue())

    def test_write_sourcemap_source_mapping_url_manual(self):
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'srcfinal.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'srcfinal.js.map')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [join(root, 'src', 'src1.js'), join(root, 'src', 'src2.js')]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream,
            source_mapping_url='src.map')

        self.assertEqual({
            "version": 3,
            "sources": ['src/src1.js', 'src/src2.js'],
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": 'srcfinal.js',
        }, json.loads(sourcemap_stream.getvalue()))
        self.assertEqual(
            '\n//# sourceMappingURL=src.map\n', output_stream.getvalue())

    def test_write_sourcemap_source_mapping_url_none(self):
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'srcfinal.js')
        sourcemap_stream = StringIO()
        sourcemap_stream.name = join(root, 'srcfinal.js.map')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [join(root, 'src', 'src1.js'), join(root, 'src', 'src2.js')]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, sourcemap_stream,
            source_mapping_url=None)

        self.assertEqual({
            "version": 3,
            "sources": ['src/src1.js', 'src/src2.js'],
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": 'srcfinal.js',
        }, json.loads(sourcemap_stream.getvalue()))
        self.assertEqual('', output_stream.getvalue())

    def test_write_sourcemap_source_mapping_same_output_stream(self):
        root = mktemp()
        output_stream = StringIO()
        output_stream.name = join(root, 'srcfinal.js')
        output_stream.write('//')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [join(root, 'src', 'src1.js'), join(root, 'src', 'src2.js')]
        names = ['foo']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, output_stream,
            source_mapping_url='src.map')

        output = output_stream.getvalue()
        # the sourcemap is written as a sourceMappingURL, with the
        # source_mapping_url argument ignored.
        self.assertIn(
            '# sourceMappingURL=data:application/json;base64;charset=utf8',
            output,
        )
        # decode the base64 string
        self.assertEqual({
            "version": 3,
            "sources": ['src/src1.js', 'src/src2.js'],
            "names": ["foo"],
            "mappings": "AAAAA",
            "file": 'srcfinal.js',
        }, json.loads(base64.b64decode(
            output.splitlines()[-1].split(',')[-1].encode('utf8')
        ).decode('utf8')))

    def test_write_sourcemap_source_mapping_encoded_same(self):
        root = mktemp()
        # emulating a codecs.open with encoding as shift_jis
        raw_stream = BytesIO()
        raw_stream.encoding = 'shift_jis'
        raw_stream.name = join(root, 'lang.js')
        output_stream = codecs.getwriter(raw_stream.encoding)(raw_stream)
        output_stream.write('yes\u306f\u3044//')
        mappings = [[(0, 0, 0, 0, 0)]]
        sources = [join(root, 'src', 'ja.js')]
        names = ['yes\u306f\u3044']

        sourcemap.write_sourcemap(
            mappings, sources, names, output_stream, output_stream,
            source_mapping_url='src.map')

        encoded = raw_stream.getvalue().splitlines()[-1]
        # the sourcemap is written as a sourceMappingURL, with the
        # source_mapping_url argument ignored.
        self.assertIn(b'application/json;base64;charset=shift_jis', encoded)
        # decode the base64 string; note the shift_jis encoding
        self.assertEqual({
            "version": 3,
            "sources": ['src/ja.js'],
            "names": ["yes\u306f\u3044"],
            "mappings": "AAAAA",
            "file": 'lang.js',
        }, json.loads(base64.b64decode(
            encoded.split(b',')[-1]).decode('shift_jis')))
