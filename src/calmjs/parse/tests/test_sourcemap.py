# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import textwrap
from io import StringIO

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
        self.assertEqual(names.update('hello'), 0)
        self.assertEqual(names.update('hello'), 0)
        self.assertIs(names.update(None), None)
        self.assertEqual(names.update('goodbye'), 1)
        self.assertEqual(names.update('goodbye'), 0)


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
        self.assertEqual(book.sink_column, 0)
        self.assertEqual(book.source_line, 0)
        self.assertEqual(book.source_column, 0)
        book.sink_sink_column = 0
        book.source_line = 1
        book.source_column = 1
        self.assertEqual(book.sink_column, 0)
        self.assertEqual(book.source_line, 0)
        self.assertEqual(book.source_column, 0)


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


class SourceMapTestCase(unittest.TestCase):

    def test_source_map_basic(self):
        stream = StringIO()

        fragments = [
            ('console', 1, 1, None),
            ('.', 1, 8, None),
            ('log', 1, 9, None),
            ('(', 1, 12, None),
            ('"hello world"', 1, 13, None),
            (')', 1, 26, None),
            (';', 1, 27, None),
        ]

        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_source_map_inferred(self):
        stream = StringIO()

        # Note the None values, as that signifies inferred elements.
        fragments = [
            ('console', 1, 1, None),
            ('.', 1, 8, None),
            ('log', 1, 9, None),
            ('(', 0, 0, None),
            ('"hello world"', 1, 13, None),
            (')', 0, 0, None),
            (';', 0, 0, None),
        ]

        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log("hello world");')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_source_map_known_standard_newline(self):
        # for cases where pretty printing happened
        # e.g. (function() { console.log("hello world"); })()
        # with all values known.
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        fragments = [
            ('(', 1, 1, None),
            ('function', 1, 2, None),
            ('(', 1, 10, None),
            (') ', 1, 11, None),
            ('{\n', 1, 13, None),
            # may be another special case here, to normalize the _first_
            # fragment
            ('  ', None, None, None),
            ('console', 1, 15, None),
            ('.', 1, 22, None),
            ('log', 1, 23, None),
            ('(', 1, 26, None),
            ('"hello world"', 1, 27, None),
            (')', 1, 40, None),
            (';\n', 1, 41, None),
            ('}', 1, 43, None),
            (')', 1, 44, None),
            ('(', 1, 45, None),
            (')', 1, 46, None),
            (';', 1, 47, None),
        ]
        names, mapping = sourcemap.write(fragments, stream, normalize=False)
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
        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(
            [[(0, 0, 0, 0)], [(2, 0, 0, 14)], [(0, 0, 0, 28)]], mapping)

    def test_source_map_inferred_standard_newline(self):
        # for cases where pretty printing happened
        # e.g. (function() { console.log("hello world"); })()
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        fragments = [
            ('(', 1, 1, None),
            ('function', 1, 2, None),
            ('(', 1, 10, None),
            (') ', 1, 11, None),
            ('{\n', 1, 13, None),
            # may be another special case here, to normalize the _first_
            # fragment
            ('  ', None, None, None),
            ('console', 1, 15, None),
            ('.', 1, 22, None),
            ('log', 1, 23, None),
            ('(', 0, 0, None),
            ('"hello world"', 1, 27, None),
            (')', 0, 0, None),
            (';\n', 0, 0, None),
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
            ('}', 1, 43, None),    # this one cannot be inferred.
            (')', 0, 0, None),  # this one can be.
            ('(', 1, 45, None),    # next starting symbol
            (')', 1, 46, None),
            (';', 0, 0, None),
        ]
        names, mapping = sourcemap.write(fragments, stream, normalize=False)
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
        names, mapping = sourcemap.write(fragments, stream)
        # the normalized version should also have the correct offsets
        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(
            [[(0, 0, 0, 0)], [(2, 0, 0, 14)], [(0, 0, 0, 28)]], mapping)

    def test_source_map_inferred_trailing_newline(self):
        err = setup_logger(self, sourcemap.logger)
        stream = StringIO()
        # Note the None values, as that signifies inferred elements.
        fragments = [
            ('console.log(\n  "hello world");', 1, 1, None),
        ]
        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), 'console.log(\n  "hello world");')
        self.assertEqual(names, [])
        self.assertEqual([
            [(0, 0, 0, 0)],
            [(0, 0, 0, 12)],
        ], mapping)
        self.assertIn(
            "WARNING text in the generated document at line 2", err.getvalue())

    def test_source_map_renamed(self):
        stream = StringIO()

        fragments = [
            ('a', 1, 1, 'console'),
            ('.', 1, 8, None),
            ('b', 1, 9, 'log'),
            ('(', 1, 12, None),
            ('"hello world"', 1, 13, None),
            (')', 1, 26, None),
            (';', 1, 27, None),
        ]

        names, mapping = sourcemap.write(fragments, stream)
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
            (' ', 0, 0, None),  # was two spaces, now single space.
            (' ', 0, 0, None),
            ('console', 1, 5, None),
            ('.', 1, 12, None),
            ('log', 1, 13, None),
            ('(', 0, 0, None),
            ('(', 0, 0, None),
            ('"hello world"', 1, 18, None),
            (')', 0, 0, None),
            (')', 0, 0, None),
            (';', 0, 0, None),
        ]

        names, mapping = sourcemap.write(fragments, stream, normalize=False)
        self.assertEqual(stream.getvalue(), '  console.log(("hello world"));')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [[
            (0, 0, 0, 0), (1, 0, 0, 1),
            (1, 0, 0, 3), (7, 0, 0, 7), (1, 0, 0, 1), (3, 0, 0, 3),
            (1, 0, 0, 1), (1, 0, 0, 1), (13, 0, 0, 13), (1, 0, 0, 1),
            (1, 0, 0, 1),
        ]])

        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(mapping, [
            [(0, 0, 0, 0), (2, 0, 0, 4)],
        ])

    def test_source_map_unmapped_initial_indent(self):
        stream = StringIO()

        fragments = [
            ('  ', None, None, None),
            ('console', 1, 1, None),
            ('.', 1, 8, None),
            ('log', 1, 9, None),
            ('(', 0, 0, None),
            ('"hello world"', 1, 13, None),
            (')', 0, 0, None),
            (';', 0, 0, None),
        ]

        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), '  console.log("hello world");')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(2, 0, 0, 0)],
        ])

    def test_source_map_mapped_initial_indent(self):
        stream = StringIO()

        fragments = [
            ('  ', 1, 1, None),
            ('console', 1, 3, None),
            ('.', 1, 10, None),
            ('log', 1, 11, None),
            ('(', 0, 0, None),
            ('"hello world"', 1, 15, None),
            (')', 0, 0, None),
            (';', 0, 0, None),
        ]

        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual(stream.getvalue(), '  console.log("hello world");')
        self.assertEqual(names, [])
        self.assertEqual(mapping, [
            [(0, 0, 0, 0)],
        ])

    def test_multiple_unmapped_chunks(self):
        stream = StringIO()

        fragments = [
            (' ', None, None, None),
            (' ', None, None, None),
            (' ', None, None, None),
            ('x', 1, 1, None),
            ('x', 1, 1, None),
            ('x', 1, 1, None),
            (' ', None, None, None),
            (' ', None, None, None),
            (' ', None, None, None),
            ('y', 1, 3, None),
            ('y', 1, 3, None),
            ('y', 1, 3, None),
        ]

        names, mapping = sourcemap.write(fragments, stream)
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
            ('(', None, None, None),
            ('function', None, None, None),
            ('(', None, None, None),
            (') ', None, None, None),
            ('{\n', None, None, None),
            # may be another special case here, to normalize the _first_
            # fragment
            ('  ', None, None, None),
            ('console', 1, 1, None),
            ('.', None, None, None),
            ('log', 1, 9, None),
            ('(', None, None, None),
            ('"hello world"', 1, 13, None),
            (')', None, None, None),
            (';', None, None, None),
            ('\n', None, None, None),
            ('}', None, None, None),
            (')', None, None, None),
            ('(', 0, None, None),  # testing for alternative conds.
            (')', None, 0, None),
            (';', None, None, None),
        ]
        names, mapping = sourcemap.write(fragments, stream, normalize=False)
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
        names, mapping = sourcemap.write(fragments, stream)
        self.assertEqual([[], [
            (2, 0, 0, 0), (7,), (1, 0, 0, 8), (3,), (1, 0, 0, 4), (13,),
        ], []], mapping)
