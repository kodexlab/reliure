#-*- coding:utf-8 -*-
from __future__ import unicode_literals
import unittest

from reliure.types import Numeric, Text
from reliure.exceptions import ValidationError

from reliure.schema import DocField, ValueField, VectorField, SetField, ListField, Schema, Doc, SchemaError

class TestDocFields(unittest.TestCase):
    """ test ot DocField subclasses
    """

    def setUp(self):
        pass

    def test_DocField(self):
        df = DocField(Numeric())
        # check is abstract
        self.assertRaises(NotImplementedError, df.get_value)
        # check that 
        self.assertRaises(AssertionError, DocField, 1)

    def test_DocField_FromType(self):
        """ Test DocField.FromType factory
        """
        self.assertIsInstance(DocField.FromType(Numeric()), ValueField)
        self.assertIsInstance(DocField.FromType(Numeric(multi=True)), ListField)
        self.assertIsInstance(DocField.FromType(Numeric(multi=True, uniq=True)), SetField)
        self.assertIsInstance(DocField.FromType(Numeric(uniq=True)), SetField)
        self.assertIsInstance(DocField.FromType(Numeric(attrs={"score": Numeric()})), VectorField)

    def test_ValueField(self):
        with self.assertRaises(SchemaError):
            vfield = ValueField(Numeric(multi=True))
        with self.assertRaises(SchemaError):
            vfield = ValueField(Numeric(multi=True, uniq=True))
        with self.assertRaises(SchemaError):
            vfield = ValueField(Numeric(attrs={"size": Numeric()}))
        vfield = ValueField(Numeric())
        self.assertRaises(ValidationError, vfield.set, "op")
        vfield.set(5)
        self.assertEqual(vfield.get_value(), 5)

    def test_SetField(self):
        with self.assertRaises(SchemaError):
            set_field = SetField(Numeric())
        with self.assertRaises(SchemaError):
            set_field = SetField(Numeric(multi=True, default={1,2,3,}))
        with self.assertRaises(SchemaError):
            set_field = SetField(Numeric(multi=True, uniq=False))
        set_field = SetField(Numeric(uniq=True, default={1,2,3,}))
        # get_value()
        self.assertEqual(set_field.get_value(), set_field)
        # test default default
        self.assertEqual(set_field, set([1,2,3]))
        # remove clear and add
        set_field.remove(2)
        self.assertEqual(set_field, set([1,3]))
        set_field.clear()
        set_field.add(1)
        self.assertEqual(set_field, set([1]))
        # set
        set_field.set([])
        self.assertEqual(set_field, set([]))
        set_field.set((4, 5, 6))
        self.assertEqual(set_field, set([4, 5, 6]))
        # test errors
        self.assertRaises(SchemaError, set_field.set, 'boo')
        self.assertRaises(SchemaError, set_field.set, 57)
        # > test than the failed set didn't change values
        self.assertEqual(set_field, set([4, 5, 6]))
        self.assertRaises(ValidationError, set_field.add, 'boo')

    def test_ListField(self):
        with self.assertRaises(SchemaError):
            l_field = ListField(Numeric())
        with self.assertRaises(SchemaError):
            l_field = ListField(Numeric(uniq=True))
        with self.assertRaises(SchemaError):
            l_field = ListField(Numeric(attrs={"size": Numeric()}))
        # affectation with append
        l_field = ListField(Numeric(multi=True))
        for x in xrange(5):
            l_field.append(x)
        self.assertEqual(l_field, [0, 1, 2, 3, 4])
        # get_value()
        self.assertEqual(l_field.get_value(), l_field)
        # affectation with set
        l_field2 = ListField(Numeric(multi=True))
        l_field2.set(xrange(5))
        self.assertEqual(l_field2, list(xrange(5)))
        # affectation fail
        self.assertRaises(SchemaError, l_field2.set, 'boo')
        self.assertRaises(SchemaError, l_field2.set, 57)
        # > test than the failed set didn't change values
        self.assertEqual(l_field2, list(xrange(5)))
        # add and append
        l_field2.add(55)
        self.assertEqual(l_field2, [0, 1, 2, 3, 4, 55])
        self.assertRaises(ValidationError, l_field2.append, "e")
        # slicing
        l_field[1:3] = [5,6]
        self.assertEqual(l_field, [0, 5, 6, 3, 4])
        self.assertEqual(l_field[3:5], [3, 4])
        with self.assertRaises(AssertionError):
            l_field[1:3] = [5,6,4]
        # remove element
        del l_field[1]
        self.assertEqual(l_field, [0, 6, 3, 4])

    def test_VectorField_base(self):
        # create a simple field
        v_field = VectorField(Text(
            attrs={
                'tf': Numeric(default=1),
                'positions': Numeric(multi=True),
            }
        ))
        # str and repr
        self.assertNotEqual(str(v_field), "")
        self.assertNotEqual(repr(v_field), "")
        # list attribute names
        self.assertSetEqual(v_field.attribute_names(), set(['tf', 'positions']))
        # get_value()
        self.assertEqual(v_field.get_value(), v_field)
        # set
        v_field.set(["un", "deux", "trois"])
        self.assertTrue(v_field.has("un"))
        self.assertTrue(v_field.has("deux"))
        self.assertTrue(v_field.has("trois"))
        self.assertEqual(len(v_field), 3)
        v_field.set([])
        self.assertEqual(len(v_field), 0)
        # add a key
        v_field.add("chat")
        self.assertEqual(len(v_field), 1)
        self.assertTrue(v_field.has("chat"))
        self.assertTrue("chat" in v_field)
        self.assertFalse("cat" in v_field)
        v_field.add("cat")
        self.assertListEqual(v_field.keys(), ["chat", "cat"])
        # iter
        self.assertListEqual(v_field.keys(), [key for key in v_field])
        
        # test attributes, by direct method call
        self.assertEqual(v_field.get_attr_value("cat", "tf"), 1)
        self.assertEqual(v_field.get_attr_value("cat", "positions"), [])

    def test_VectorField_VectorItem(self):
        # create a simple field
        v_field = VectorField(Text(
            attrs={
                'tf': Numeric(default=1),
                'positions': Numeric(multi=True),
            }
        ))
        v_field.set(["chat", "cat"])
        # test attributes throw *VectorItem*
        self.assertEqual(v_field["cat"].tf, 1)
        v_field["cat"]["tf"] = 80
        self.assertEqual(v_field["cat"].tf, 80)
        v_field["cat"].tf = 15
        self.assertEqual(v_field["cat"].tf, 15)
        self.assertListEqual(v_field["chat"].positions, [])
        v_field["chat"].positions.add(45)
        v_field["chat"].positions.add(4)
        self.assertListEqual(v_field["chat"].positions, [45, 4])
        self.assertSetEqual(v_field["chat"].attribute_names(), set(['tf', 'positions']))
        self.assertDictEqual(v_field["chat"].as_dict(), {'positions': [45, 4], 'tf': 1})

    def test_VectorField_VectorAttr(self):
        # create a simple field
        v_field = VectorField(Text(
            attrs={
                'tf': Numeric(default=1),
                'positions': Numeric(multi=True),
            }
        ))
        v_field.set(["chat", "cat"])
        # test attributes throw *VectorAttr*
        v_field["cat"].tf = 15
        self.assertListEqual(v_field.tf.values(), [1, 15])
        self.assertEqual(v_field.tf[0], 1)         # getitem
        self.assertEqual(v_field.tf[1], 15)
        v_field.tf[1] = 500                        # setitem
        self.assertEqual(v_field.tf[1], 500)
        self.assertListEqual(v_field.tf[0:2], [1, 500]) # getslice
        v_field.tf = [2, 3]
        with self.assertRaises(SchemaError):
            v_field.tf = [2, 3, 45, 4]
        with self.assertRaises(SchemaError):
            var = v_field.cat
        with self.assertRaises(SchemaError):
            v_field.cat = 12
        # add an atribute
        with self.assertRaises(SchemaError):
            v_field.add_attribute("tf", Numeric())
        v_field.add_attribute("score", Numeric(default=0))
        self.assertSetEqual(v_field.attribute_names(), set(['tf', 'positions', 'score']))



class TestDoc(unittest.TestCase):

    maxDiff = None

    def test_doc(self):
        schema = Schema(titre = Text())
        doc = Doc(schema)
        self.assertTrue("titre" in doc.schema)
        # no equal because DocNum added
        self.assertNotEqual(doc.schema, schema)
        self.assertEqual(doc["schema"], doc.schema)
        # repr, weak test, just avoid Exception
        self.assertNotEqual(repr(doc), "")
        self.assertNotEqual(doc.export(), "")
        
        # try to overide the schema
        with self.assertRaises(SchemaError):
            doc.schema = schema
        
        # init with data
        doc = Doc(schema, titre="Un document qui documente")
        self.assertEqual(doc.titre, "Un document qui documente")
        self.assertEqual(doc["titre"], "Un document qui documente")
        # change attr
        doc.titre = "Un document vide"
        self.assertEqual(doc.titre, "Un document vide")
        
        # add a field
        doc.nb_pages = Numeric()
        self.assertTrue("nb_pages" in doc.schema)
        doc.nb_pages = 24
        self.assertEqual(doc.nb_pages, 24)
        with self.assertRaises(SchemaError):
            doc.nb_page = 24
        with self.assertRaises(SchemaError):
            nb_page = doc.nb_page
        with self.assertRaises(SchemaError):
            doc.add_field("nb_pages", Numeric())
        
        # add a more complex field
        doc.add_field("authors", Text(multi=True, uniq=True))
        self.assertTrue("authors" in doc)
        doc.authors.add("Jule Rime")
        doc.authors.add("Jule Rime")
        doc.authors.add("Lise Liseuse")
        self.assertEqual(len(doc.authors), 2)
        
    
    def test_doc_analyse(self):
        from collections import OrderedDict
        text = u"i have seen chicken passing the street and i believed "\
           +"how many chicken must pass in the street before you believe"
        # text analyse 
        tokens = text.split(' ')
        #crop = lambda term, max_length : term[:min(max_length, len(term))] 
        #tokens = [crop(term,5) for term in text]
        text_terms =  list(OrderedDict.fromkeys(tokens))
        terms_tf = [tokens.count(k) for k in text_terms]
        terms_pos = [[i for i, x in enumerate(tokens) if x == k ] for k in text_terms]
        
        # document
        term_field = Text(multi=True, uniq=True, 
                          attrs={'tf':Numeric(default=1),
                                 'positions':Numeric(multi=True),})
        schema = Schema(docnum=Numeric(), title=Text(), text=Text(), terms=term_field)
        doc = Doc(schema, docnum=1, text=text, title=u"chickens")
        doc.terms = text_terms
        self.assertEqual(doc.terms.tf.values(), [1]*len(text_terms)) 
        doc.terms.tf = terms_tf
        doc.terms.positions = terms_pos
        self.assertEqual(doc.terms['chicken'].positions, [3, 12])
        self.assertEqual(doc.terms['chicken'].tf, 2)
        self.assertEqual(doc.title, "chickens")
        
        expect = {
         'docnum': 1, 
         'text': u'i have seen chicken passing the street and i believed how many chicken must pass in the street before you believe', 
         'terms': {
            'keys': {u'and': 7, u'before': 14, u'believe': 16, u'believed': 8,
                u'chicken': 3, u'have': 1, u'how': 9, u'i': 0, u'in': 13,
                u'many': 10, u'must': 11, u'pass': 12, u'passing': 4,
                u'seen': 2, u'street': 6, u'the': 5, u'you': 15},
            'tf': [2, 1, 1, 2, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            'positions': [[0, 8], [1], [2], [3, 12], [4], [5, 16], [6, 17], [7],
            [9],[10], [11], [13], [14], [15], [18], [19], [20]]
          }, 
          'title': u'chickens'
        } 
       
        self.assertEqual(doc.export(), expect)
