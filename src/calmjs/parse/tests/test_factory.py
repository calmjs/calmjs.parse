# -*- coding: utf-8 -*-
import unittest

from calmjs.parse import asttypes
from calmjs.parse.factory import Factory
from calmjs.parse.factory import AstTypesFactory


class FactoryTestCase(unittest.TestCase):

    def test_basic(self):
        # a quick and dirty classes and a container
        class A(object):
            pass

        class B(object):
            pass

        class O(object):
            pass

        def dummy_str(s):
            return '%d' % ord(s.__class__.__name__)

        def dummy_repr(s):
            return '0x%x' % ord(s.__class__.__name__)

        o = O()
        o.A = A
        o.B = B

        factory = Factory(o, dummy_str, dummy_repr)
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
