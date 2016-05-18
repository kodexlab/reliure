#-*- coding:utf-8 -*-
from __future__ import unicode_literals

import unittest
from pytest import raises

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
        with raises(NotImplementedError):
            df.get_value()
        # check that 
        with raises(AssertionError):
            df2 = DocField(1)

    def test_DocField_FromType(self):
        """ Test DocField.FromType factory
        """
        assert isinstance(DocField.FromType(Numeric()), ValueField)
        assert isinstance(DocField.FromType(Numeric(multi=True)), ListField)
        assert isinstance(DocField.FromType(Numeric(multi=True, uniq=True)), SetField)
        assert isinstance(DocField.FromType(Numeric(uniq=True)), SetField)
        assert isinstance(DocField.FromType(Numeric(attrs={"score": Numeric()})), VectorField)

    def test_ValueField(self):
        with raises(SchemaError):
            vfield = ValueField(Numeric(multi=True))
        with raises(SchemaError):
            vfield = ValueField(Numeric(multi=True, uniq=True))
        with raises(SchemaError):
            vfield = ValueField(Numeric(attrs={"size": Numeric()}))
        vfield = ValueField(Numeric())
        with raises(ValidationError):
            vfield.set("op")
        vfield.set(5)
        assert vfield.get_value() == 5

    def test_SetField(self):
        with raises(SchemaError):
            set_field = SetField(Numeric())
        with raises(SchemaError):
            set_field = SetField(Numeric(multi=True, default={1,2,3,}))
        with raises(SchemaError):
            set_field = SetField(Numeric(multi=True, uniq=False))
        set_field = SetField(Numeric(uniq=True, default={1,2,3,}))
        # get_value()
        assert set_field.get_value() == set_field
        # test default default
        assert set_field == set([1,2,3])
        # remove clear and add
        set_field.remove(2)
        assert set_field == set([1,3])
        set_field.clear()
        set_field.add(1)
        assert set_field == set([1])
        # set
        set_field.set([])
        assert set_field == set([])
        set_field.set((4, 5, 6))
        assert set_field, set([4, 5 == 6])
        # test errors
        with raises(SchemaError):
            set_field.set('boo')
        with raises(SchemaError):
            set_field.set(57)
        # > test than the failed set didn't change values
        assert set_field, set([4, 5 == 6])
        with raises(ValidationError):
            set_field.add('boo')

    def test_ListField(self):
        with raises(SchemaError):
            l_field = ListField(Numeric())
        with raises(SchemaError):
            l_field = ListField(Numeric(uniq=True))
        with raises(SchemaError):
            l_field = ListField(Numeric(attrs={"size": Numeric()}))
        # affectation with append
        l_field = ListField(Numeric(multi=True))
        for x in range(5):
            l_field.append(x)
        assert l_field == [0, 1, 2, 3, 4]
        # get_value()
        assert l_field.get_value() == l_field
        # affectation with set
        l_field2 = ListField(Numeric(multi=True))
        l_field2.set(range(5))
        assert l_field2 == list(range(5))
        # affectation fail
        with raises(SchemaError):
            l_field2.set('boo')
        with raises(SchemaError):
            l_field2.set(57)
        # > test than the failed set didn't change values
        assert l_field2 == list(range(5))
        # add and append
        l_field2.add(55)
        assert l_field2 == [0, 1, 2, 3, 4, 55]
        with raises(ValidationError):
            l_field2.append("e")
        # slicing
        l_field[1:3] = [5,6]
        assert l_field == [0, 5, 6, 3, 4]
        assert l_field[3:5] == [3, 4]
        with raises(ValueError):
            l_field[1:3] = [5,6,4]
        # remove element
        del l_field[1]
        assert l_field == [0, 6, 3, 4]

    def test_VectorField_base(self):
        # create a simple field
        v_field = VectorField(Text(
            attrs={
                'tf': Numeric(default=1),
                'positions': Numeric(multi=True),
            }
        ))
        # str and repr
        assert str(v_field) != ""
        assert repr(v_field) != ""
        # list attribute names
        assert v_field.attribute_names() == set(['tf', 'positions'])
        # get_value()
        assert v_field.get_value() == v_field
        # set
        v_field.set(["un", "deux", "trois"])
        assert v_field.has("un")
        assert v_field.has("deux")
        assert v_field.has("trois")
        assert len(v_field) == 3
        v_field.set([])
        assert len(v_field) == 0
        # add a key
        v_field.add("chat")
        assert len(v_field) == 1
        assert v_field.has("chat")
        assert "chat" in v_field
        assert not "cat" in v_field
        v_field.add("cat")
        assert list(v_field) == ["chat", "cat"] # check v_field.keys()
        
        # test attributes, by direct method call
        assert v_field.get_attr_value("cat", "tf") == 1
        assert v_field.get_attr_value("cat", "positions") == []

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
        assert v_field["cat"].tf == 1
        v_field["cat"]["tf"] = 80
        assert v_field["cat"].tf == 80
        v_field["cat"].tf = 15
        assert v_field["cat"].tf == 15
        assert v_field["chat"].positions == []
        v_field["chat"].positions.add(45)
        v_field["chat"].positions.add(4)
        assert v_field["chat"].positions == [45, 4]
        assert v_field["chat"].attribute_names() == set(['tf', 'positions'])
        assert v_field["chat"].as_dict() == {'positions': [45, 4], 'tf': 1}

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
        assert v_field.tf.values() == [1, 15]
        assert v_field.tf[0] == 1         # getitem
        assert v_field.tf[1] == 15
        v_field.tf[1] = 500                        # setitem
        assert v_field.tf[1] == 500
        assert v_field.tf[0:2] == [1, 500] # getslice
        v_field.tf = [2, 3]
        with raises(SchemaError):
            v_field.tf = [2, 3, 45, 4]
        with raises(SchemaError):
            var = v_field.cat
        with raises(SchemaError):
            v_field.cat = 12
        # add an atribute
        with raises(SchemaError):
            v_field.add_attribute("tf", Numeric())
        v_field.add_attribute("score", Numeric(default=0))
        assert v_field.attribute_names() == set(['tf', 'positions', 'score'])



class TestDoc(unittest.TestCase):

    maxDiff = None

    def test_doc(self):
        schema = Schema(titre = Text())
        doc = Doc(schema)
        assert "titre" in doc.schema
        # no equal because DocNum added
        assert doc.schema != schema
        assert doc["schema"] == doc.schema
        # repr, weak test, just avoid Exception
        assert repr(doc) != ""
        assert doc.export() != ""
        
        # try to overide the schema
        with raises(SchemaError):
            doc.schema = schema
        
        # init with data
        doc = Doc(schema, titre="Un document qui documente")
        assert doc.titre == "Un document qui documente"
        assert doc["titre"] == "Un document qui documente"
        # change attr
        doc.titre = "Un document vide"
        assert doc.titre == "Un document vide"
        
        # add a field
        doc.nb_pages = Numeric()
        assert "nb_pages" in doc.schema
        doc.nb_pages = 24
        assert doc.nb_pages == 24
        with raises(SchemaError):
            doc.nb_page = 24
        with raises(SchemaError):
            nb_page = doc.nb_page
        with raises(SchemaError):
            doc.add_field("nb_pages", Numeric())
        
        # add a more complex field
        doc.add_field("authors", Text(multi=True, uniq=True))
        assert "authors" in doc
        doc.authors.add("Jule Rime")
        doc.authors.add("Jule Rime")
        doc.authors.add("Lise Liseuse")
        assert len(doc.authors) == 2
        
    
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
        assert doc.terms.tf.values() == [1]*len(text_terms) 
        doc.terms.tf = terms_tf
        doc.terms.positions = terms_pos
        assert doc.terms['chicken'].positions == [3, 12]
        assert doc.terms['chicken'].tf == 2
        assert doc.title == "chickens"
        
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
       
        assert doc.export() == expect
