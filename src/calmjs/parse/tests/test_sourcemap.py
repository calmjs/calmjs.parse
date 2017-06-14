# -*- coding: utf-8 -*-
import unittest

from calmjs.parse import sourcemap


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
        book.foo = 124
        self.assertEqual(book.foo, 1)
        self.assertEqual(book.foo, 1)
        book.foo = 1
        self.assertEqual(book.foo, -123)
        self.assertEqual(book.foo, -123)
        book.foo = 1
        self.assertEqual(book.foo, 0)
        self.assertEqual(book.foo, 0)
        book.foo = 1
        self.assertEqual(book.foo, 0)
        self.assertEqual(book.foo, 0)
        book.foo = 2
        book.foo = 2
        self.assertEqual(book.foo, 0)

    def test_reset(self):
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

    def test_unmodified(self):
        # this is a typical canonical example
        # console.log("hello world");
        remapped = sourcemap.normalize_mapping_line([
            (0, 0, 0, 0),
            (7, 0, 0, 7),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
        ])
        self.assertEqual([(0, 0, 0, 0)], remapped)

    def test_unmodified_offsetted(self):
        # simulate the removal of indentation
        remapped = sourcemap.normalize_mapping_line([
            (0, 0, 0, 2),
            (7, 0, 0, 7),
            (1, 0, 0, 1),
            (3, 0, 0, 3),
            (1, 0, 0, 1),
            (13, 0, 0, 13),
            (1, 0, 0, 1),
        ])
        self.assertEqual([(0, 0, 0, 2)], remapped)

    def test_five_segment(self):
        remapped = sourcemap.normalize_mapping_line([
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

    def test_file_changed(self):
        remapped = sourcemap.normalize_mapping_line([
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

    def test_line_changed(self):
        remapped = sourcemap.normalize_mapping_line([
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

    def test_column_offset(self):
        remapped = sourcemap.normalize_mapping_line([
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
