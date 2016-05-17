#-*- coding:utf-8 -*-
import unittest

from reliure.types import Text, Numeric
from reliure.schema import Schema, SchemaError

class TestFieldTypes(unittest.TestCase):
    def setUp(self):
        pass

    def test_schema(self):
        # create a schema
        schema = Schema(title=Text(), rank=Numeric())
        
        self.assertNotEqual(repr(schema), "")
        # field count 
        self.assertEqual(len(schema), 2)
        # list field names
        self.assertTrue('title' in schema.field_names())
        self.assertTrue('rank' in schema.field_names())
        self.assertFalse('score' in schema.field_names())
        # acces private "_field" attr_name
        self.assertEqual(len(schema._fields), 2)
        self.assertEqual(len(schema["_fields"]), 2)
        self.assertTrue('rank' in schema._fields)
        self.assertFalse('score' in schema._fields)
        # test field by name
        self.assertTrue(schema.has_field('title'))
        self.assertFalse(schema.has_field('boo'))
        # get by attr
        self.assertEqual(schema.title, schema['title'])
        self.assertRaises(SchemaError, lambda : schema['boo'])
        
        # add new field
        schema.add_field('text', Text())
        self.assertTrue('text' in schema.field_names())
        self.assertEqual(len(schema), 3)
        # invalid field names
        self.assertRaises(SchemaError, schema.add_field, "_text", Text())
        self.assertRaises(SchemaError, schema.add_field, "te xt", Text())
        self.assertRaises(SchemaError, schema.add_field, "text", Text())
        # invalid field
        self.assertRaises(SchemaError, schema.add_field, "a", [])
        # Fields iterator
        schema.iter_fields()
        names1 = [name for name, fieldtype in schema.iter_fields()]
        names2 = [name for name in schema]
        self.assertEqual(len(names1), 3)
        self.assertListEqual(names1, names2)

        # remove field
        # unimplemented
        field_name = "text"
        self.assertRaises(NotImplementedError, schema.remove_field, field_name)
        
        # test copy
        schema_bis = schema.copy()
        self.assertTrue(schema_bis.has_field('title'))
        self.assertFalse(schema_bis.has_field('boo'))
        
