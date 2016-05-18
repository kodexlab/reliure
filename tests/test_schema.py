#-*- coding:utf-8 -*-
import unittest
from pytest import raises

from reliure.types import Text, Numeric
from reliure.schema import Schema, SchemaError

class TestFieldTypes(unittest.TestCase):
    def setUp(self):
        pass

    def test_schema(self):
        # create a schema
        schema = Schema(title=Text(), rank=Numeric())
        
        assert repr(schema) != ""
        # field count 
        assert len(schema) == 2
        # list field names
        assert 'title' in schema.field_names()
        assert 'rank' in schema.field_names()
        assert not 'score' in schema.field_names()
        # acces private "_field" attr_name
        assert len(schema._fields) == 2
        assert len(schema["_fields"]) == 2
        assert 'rank' in schema._fields
        assert not 'score' in schema._fields
        # test field by name
        assert schema.has_field('title')
        assert not schema.has_field('boo')
        # get by attr
        assert schema.title == schema['title']

        with raises(SchemaError):
            boo = schema['boo']

        # add new field
        schema.add_field('text', Text())
        assert 'text' in schema.field_names()
        assert len(schema) == 3
        # invalid field names
        with raises(SchemaError):
            schema.add_field("_text", Text())
        with raises(SchemaError):
            schema.add_field("te xt", Text())
        with raises(SchemaError):
            schema.add_field("text", Text())
        # invalid field
        with raises(SchemaError):
            schema.add_field("a", [])
        # Fields iterator
        schema.iter_fields()
        names1 = [name for name, fieldtype in schema.iter_fields()]
        names2 = [name for name in schema]
        assert len(names1) == 3
        self.assertListEqual(names1, names2)

        # remove field
        # unimplemented
        field_name = "text"
        with raises(NotImplementedError):
            schema.remove_field(field_name)
        
        # test copy
        schema_bis = schema.copy()
        assert schema_bis.has_field('title')
        assert not schema_bis.has_field('boo')
        
