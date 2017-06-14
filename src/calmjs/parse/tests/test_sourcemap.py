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
