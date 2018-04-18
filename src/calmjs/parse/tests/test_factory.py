# -*- coding: utf-8 -*-
import unittest

from calmjs.parse import asttypes
from calmjs.parse.factory import SRFactory
from calmjs.parse.factory import AstTypesFactory


class SRFactoryTestCase(unittest.TestCase):

    def test_basic(self):
        # a quick and dirty classes and a container
        class A(object):
            pass

        class B(object):
            pass

        class Obj(object):
            pass

        def dummy_str(s):
            return '%d' % ord(s.__class__.__name__)

        def dummy_repr(s):
            return '0x%x' % ord(s.__class__.__name__)

        o = Obj()
        o.A = A
        o.B = B

        factory = SRFactory(o, dummy_str, dummy_repr)
        a = A()
        wrapped_a = factory.A()
        self.assertNotEqual(str(a), '65')
        self.assertNotEqual(repr(a), '0x41')
        self.assertEqual(str(wrapped_a), '65')
        self.assertEqual(repr(wrapped_a), '0x41')

        with self.assertRaises(AttributeError):
            factory.C()

    def test_asttypes(self):

        def dummy_str(s):
            return 'This is a %s' % s.__class__.__name__

        def dummy_repr(s):
            return '%s has id %x' % (s.__class__.__name__, id(s))

        custom_asttypes = AstTypesFactory(dummy_str, dummy_repr)
        normal_node = asttypes.Node()
        custom_node = custom_asttypes.Node()

        self.assertTrue(isinstance(custom_node, asttypes.Node))
        self.assertNotEqual(str(normal_node), 'This is a Node')
        self.assertFalse(repr(normal_node).startswith('Node has id'))
        self.assertEqual(str(custom_node), 'This is a Node')
        self.assertTrue(repr(custom_node).startswith('Node has id'))


class ParserUnparserFactoryTestCase(unittest.TestCase):

    def test_base(self):
        # simply just test the basic functions... while the top level
        # readme covers this, just ensure this covers it
        from calmjs.parse import es5

        src = u'var a;'
        self.assertTrue(isinstance(es5(src), asttypes.Node))
        self.assertEqual(es5.pretty_print(src).strip(), src)
        self.assertEqual(es5.minify_print(src), src)
        self.assertEqual(es5.minify_print(src, True, True), src)
