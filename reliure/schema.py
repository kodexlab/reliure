#-*- coding:utf-8 -*-
""" :mod:`reliure.schema`
======================

:copyright: (c) 2013 - 2014 by Yannick Chudy, Emmanuel Navarro.
:license: ${LICENSE}

inheritance diagrams
--------------------

.. inheritance-diagram:: Schema 

.. inheritance-diagram:: Doc
.. inheritance-diagram:: DocField VectorField ValueField SetField
Class
-----
"""
# python 2 and 3 compatibility
from __future__ import unicode_literals
import six
from builtins import range

from collections import OrderedDict

from reliure.types import GenericType, Numeric, Text
from reliure.exceptions import ValidationError


class SchemaError(Exception):
    """ Error """
    pass

class FieldValidationError(Exception):
    """ Error in a field validation """
    def __init__(self, field, value, errors):
        super(FieldValidationError, self).__init__(field)
        self.field = field
        self.value = value
        self.errors = errors

    def __repr__(self):
        return "<FieldValidationError '%s', '%s'>" % (self.field, self.value)
        
    def __str__(self):
        return "FieldValidationError '%s' : %s \n  %s " % (self.field, self.value, 
                            "\n".join([ "\t*%s" % err for err in self.errors]))



class Schema(object):
    """ Schema definition for documents (:class:`Doc`).
    Class inspired from Matt Chaput's Whoosh.
    
    Creating a schema:
    
    >>> from reliure.types import Text, Numeric
    >>> schema = Schema(title=Text(), score=Numeric())
    >>> sorted(schema.field_names())
    ['score', 'title']
    """

    def __init__(self, **fields):
        """ Create a schema from pairs of field name and field type
        
        For exemple:
        
        >>> from reliure.types import Text, Numeric
        >>> schema = Schema(tags=Text(multi=True), score=Numeric(vtype=float, min=0., max=1.))
        """
        self._fields = {}
        # Create fields
        for name, fieldtype in six.iteritems(fields):
            self.add_field(name, fieldtype)

    def copy(self):
        """ Returns a copy of the schema
        """
        return Schema(**self._fields)

    def add_field(self, name, field):
        """ Add a named field to the schema.
        
        .. Warning:: the field name should not contains spaces and should not
            start with an underscore.
        
        :param name: name of the new field
        :type name: str
        :param field: type instance for the field 
        :type field: subclass of :class:`.GenericType`
        """
        # testing names 
        if name.startswith("_"):
            raise SchemaError("Field names cannot start with an underscore.")
        if " " in name:
            raise SchemaError("Field names cannot contain spaces.")
        if name in self._fields:
            raise SchemaError("Schema already has a field named '%s'" % name)
        if not isinstance(field, GenericType):
            raise SchemaError("Wrong type in schema for field: %s, %s is not a GenericType" % (name, field))
        self._fields[name] = field

    def remove_field(self, field_name):
        raise NotImplementedError()

    def iter_fields(self):
        return six.iteritems(self._fields)

    def field_names(self):
        return list(self._fields)

    def has_field(self, name):
        return self.__contains__(name)

    def __iter__(self):
        return six.iterkeys(self._fields)

    def __contains__(self, name):
        return name in self._fields    

    def __len__(self): 
        """ returns field count in schema """
        return len(self._fields)

    def __getattr__(self, name): 
        return self.__getitem__(name)

    def __getitem__(self, name): 
        if name == '_fields':
            return self._fields
        elif name in self._fields:
            return self._fields[name]
        else:
            raise SchemaError("Field '%s' does not exist in Schema (%s)" % (name, self.field_names()))

    def __repr__(self):
        fields_repr = "\n".join(
            " * %s: %s" % (key, value)
            for key, value in six.iteritems(self._fields)
        )
        return "<%s:\n%s\n>" % (self.__class__.__name__, fields_repr)

###
# Document fields implementations internal use only

class DocField(object):
    """ Abstract document field
    
    Theses objects are containers of document's data.
    """
    def __init__(self, ftype):
        """
        :param ftype: the type for the field
        :type ftype: subclass of :class:`.GenericType` 
        """
        assert isinstance(ftype, GenericType)
        self._ftype = ftype

    @property
    def ftype(self):
        return self._ftype

    def get_value(self):
        """ return the value of the field.
        """
        raise NotImplementedError
    
    def parse(self, value):
        return self._ftype.parse(value)
    
    def export(self):
        """ Returns a serialisable representation of the field
        """
        raise NotImplementedError

    @staticmethod
    def FromType(ftype):
        """ DocField subclasses factory, creates a convenient field to store
        data from a given Type.

        attribute precedence :
        
        * ``|attrs| > 0`` (``multi`` and ``uniq`` are implicit) => VectorField
        * ``uniq`` (``multi`` is implicit) => SetField 
        * ``multi`` and ``not uniq`` => ListField 
        * ``not multi`` => ValueField
        
        :param ftype: the desired type of field
        :type ftype: subclass of :class:`.GenericType`
        """
        if ftype.attrs is not None and len(ftype.attrs):
            return VectorField(ftype)
        elif ftype.uniq:
            return SetField(ftype)
        elif ftype.multi:
            return ListField(ftype)
        else:
            return ValueField(ftype)


class ValueField(DocField):
    """ Stores only one value

    usage example:

    >>> from reliure.types import Text
    >>> schema = Schema(title=Text(), like=Numeric(default=45))
    >>> doc = Doc(schema, docnum='abc42')
    >>> # 'title' field
    >>> doc.title = 'Un titre cool !'
    >>> doc.title
    'Un titre cool !'
    >>> doc.get_field('title').export()
    'Un titre cool !'
    >>> doc.get_field('title').ftype
    Text(multi=False, uniq=False, default=, attrs=None)
    >>> # 'like' field
    >>> doc.like
    45
    """
    __slot__ = ['value']
    
    def __init__(self, fieldtype):
        if fieldtype.multi:
            raise SchemaError("The type of a ValueField should not be multiple")
        DocField.__init__(self, fieldtype)
        self.value = fieldtype.default
    
    def get_value(self): 
        return self.value
    
    def set(self, value):
        self.value = self._ftype.validate(value)
    
    def export(self):
        return self.get_value()


class SetField(DocField, set):
    """ Document field for a set of values (i.e. the fieldtype is "multi" and "uniq")
    
    usage example:
    
    >>> from reliure.types import Text
    >>> schema = Schema(tags=Text(multi=True, uniq=True))
    >>> doc = Doc(schema, docnum='abc42')
    >>> doc.tags.add('boo')
    >>> doc.tags.add('foo')
    >>> len(doc.tags)
    2
    >>> sorted(doc.tags.export())
    ['boo', 'foo']
    """
    #XXX; maybe it can use collections.MutableSet
    # http://docs.python.org/2/library/collections.html#collections-abstract-base-classes

    def __init__(self, fieldtype):
        if not fieldtype.uniq:
            raise SchemaError("The type of a SetField should be uniq")
        DocField.__init__(self, fieldtype)
        self.set(fieldtype.default or [])

    def add(self, value):
        set.add(self, self._ftype.validate(value))

    def get_value(self):
        # the field is a set itself...
        return self

    def set(self, values):
        if not hasattr(values, '__iter__'):
            raise SchemaError("Wrong value '%s' for field '%s'" % (values, self._ftype))
        # check data are valid before deleting the data
        # prevents losing data if wrong type is passed
        items = set(self._ftype.validate(v) for v in values)
        self.clear()
        self.update(items)

    
    def parse(self, value):
        return [ self._ftype.parse(v) for v in value ]
   
    
    def export(self):
        return list(self)


class ListField(DocField, list):
    """ list container for non-uniq field
    
    usage example:
    
    >>> from reliure.types import Text
    >>> schema = Schema(tags=Text(multi=True, uniq=False))
    >>> doc = Doc(schema, docnum='abc42')
    >>> doc.tags.add('boo')
    >>> doc.tags.add('foo')
    >>> doc.tags.add('foo')
    >>> len(doc.tags)
    3
    >>> doc.tags.export()
    ['boo', 'foo', 'foo']
    """
    #XXX; maybe it can use collections.MutableSequence
    # http://docs.python.org/2/library/collections.html#collections-abstract-base-classes
    def __init__(self, fieldtype):
        if not fieldtype.multi:
            raise SchemaError("The type of a ListField should be multiple")
        if fieldtype.uniq:
            raise SchemaError("The type of a ListField should not be uniq")
        DocField.__init__(self, fieldtype)

    def add(self, value):
        """ Adds a value to the list (as append).
        convenience method, to have the same signature than :class:`.SetField` and :class:`.VectorField`"""
        self.append(value)

    def get_value(self):
        # the field is a list itself...
        return self

    def append(self, value):
        list.append(self, self._ftype.validate(value))

    def set(self, values):
        """ set new values (values have to be iterable)
        """
        if not hasattr(values, '__iter__'):
            raise SchemaError("Wrong value '%s' for field '%s'" % (values, self._ftype))
        # check data are valid before deleting the data
        # prevents losing data if wrong type is passed
        values = [self._ftype.validate(v) for v in values]
        del self[:]
        for v in values:
            list.append(self, v)

    def parse(self, value):
        return [ self._ftype.parse(v) for v in value ]
   

    #just for python2 compatibility
    def __setslice__(self, s, c, v):
        self[slice(s,c)] = v

    def __setitem__(self, idx_or_slice, value):
        if isinstance(idx_or_slice, slice):
            sl = idx_or_slice
            if sl.stop - sl.start != len(value):
                raise ValueError("given data don't fit slice size (%s-%s != %s)" % (sl.stop, sl.start, len(value)))
            for x, xi in enumerate(range(*sl.indices(len(self)))):
                self[xi] = value[x]
        else:
            idx = idx_or_slice
            list.__setitem__(self, idx, self._ftype.validate(value))

    def export(self):
        """ returns a list pre-seriasation of the field
        
        >>> from reliure.types import Text
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True) 
        >>> doc.terms.add('rat')
        >>> doc.terms.add('chien')
        >>> doc.terms.add('chat')
        >>> doc.terms.add('léopart')
        >>> doc.terms.export()
        ['rat', 'chien', 'chat', 'l\\xe9opart']
        """
        return list(self)


class VectorField(DocField):
    """ More complex document field container

    :hide:
        >>> from pprint import pprint
  
    usage:

    >>> from reliure.types import Text, Numeric
    >>> doc = Doc(docnum='1')
    >>> doc.terms = Text(multi=True, uniq=True, attrs={'tf': Numeric()}) 
    >>> doc.terms.add('chat')
    >>> doc.terms['chat'].tf = 12
    >>> doc.terms['chat'].tf
    12
    >>> doc.terms.add('dog', tf=55)
    >>> doc.terms['dog'].tf
    55

    One can also add an atribute after the field is created:

    >>> doc.terms.add_attribute('foo', Numeric(default=42))
    >>> doc.terms.foo.values()
    [42, 42]
    >>> doc.terms['dog'].foo = 20
    >>> doc.terms.foo.values()
    [42, 20]

    It is also possible to delete elements from the field
    
    >>> pprint(doc.terms.export())
    {'foo': [42, 20], 'keys': {'chat': 0, 'dog': 1}, 'tf': [12, 55]}
    >>> del doc.terms['chat']
    >>> pprint(doc.terms.export())
    {'foo': [20], 'keys': {'dog': 0}, 'tf': [55]}
    """
    def __init__(self, ftype):
        DocField.__init__(self, ftype)
        self._attrs =  {} # attr_name : [DocField, ]    
        self._keys = OrderedDict()   # key: idx
        self.clear_attributes()

    def attribute_names(self):
        """ returns the names of field's data attributes
        
        :return: set of attribute names
        :rtype: frozenset
        """
        return frozenset(list(self._attrs))

    def add_attribute(self, name, ftype):
        """ Add a data attribute.
        Note that the field type will be modified !
        
        :param name: name of the new attribute
        :type name: str
        :param ftype: type of the new attribute
        :type ftype: subclass of :class:`.GenericType`
        """
        if name in self._ftype.attrs:
            raise SchemaError("VectorField has already attribute named '%s' (attrs: %s)" % (name, list(self._ftype.attrs)))
        # add the attr to the underlying GenericType
        self._ftype.attrs[name] = ftype
        # add the attr it self
        self._attrs[name] = [DocField.FromType(ftype) for _ in range(len(self))]
    
    def get_attribute(self, name):
        return getattr(self, name)

    def clear_attributes(self):
        """ removes all attributes
        """
        self._attrs = {} # removes all attr
        for name, attr_field in six.iteritems(self._ftype.attrs):
            self._attrs[name] = []

    def __repr__(self):
        return "<%s:%s>" % (self.__class__.__name__, list(self._ftype.attrs))

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        """ Vector keys count """
        return len(self._keys)

    def __iter__(self):
        """ It is possible to iterate over a vector field:

        >>> from reliure.types import Text, Numeric
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, uniq=True, attrs={'tf': Numeric()}) 
        >>> doc.terms.add('cat', tf=2)
        >>> doc.terms.add('dog', tf=55)
        >>> for term in doc.terms:
        ...     print(term)
        cat
        dog
        """
        return six.iterkeys(self._keys)

    def keys(self): 
        """ list of keys in the vector """
        return self._keys.keys()

    def __contains__(self, key):
        """ returns True if the vector has the specified key
        """
        return self.has(key)

    def has(self, key): 
        return key in self._keys

    def __getitem__(self, key):
        """ Returns a :class:`.VectorItem` mapping the given key
        """
        if not self.has(key):
            raise KeyError("No such key ('%s') in this field" % key)
        return VectorItem(self, key)

    def __delitem__(self, key):
        """ Delete the element from the field

        :hide:
            >>> from pprint import pprint

        >>> from reliure.types import Text, Numeric
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(attrs={'tf': Numeric()}) 
        >>> doc.terms.add('cat', tf=2)
        >>> doc.terms.add('mouse', tf=20)
        >>> doc.terms.add('bear', tf=100)
        >>> doc.terms.add('dog', tf=55)
        >>> doc.terms.add('kiwi', tf=5)
        >>> pprint(doc.terms.export())
        {'keys': {'bear': 2, 'cat': 0, 'dog': 3, 'kiwi': 4, 'mouse': 1},
        'tf': [2, 20, 100, 55, 5]}
        >>> #
        >>> # delete some elements
        >>> del doc.terms['mouse']
        >>> del doc.terms['dog']
        >>> pprint(doc.terms.export())
        {'keys': {'bear': 1, 'cat': 0, 'kiwi': 2}, 'tf': [2, 100, 5]}
        >>> len(doc.terms)
        3
        """
        if not self.has(key):
            raise KeyError("No such key ('%s') in this field" % key)
        iid = self._keys[key]
        for attr in six.itervalues(self._attrs):
            attr[iid] = None
        del self._keys[key]

    def get_value(self): 
        """ from DocField, convenient method """
        return self

    def export(self):
        """ returns a dictionary pre-seriasation of the field
        
        :hide:
            >>> from pprint import pprint
        
        >>> from reliure.types import Text, Numeric
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, uniq=True, attrs={'tf': Numeric(default=1)}) 
        >>> doc.terms.add('chat')
        >>> doc.terms.add('rat', tf=5)
        >>> doc.terms.add('chien', tf=2)
        >>> pprint(doc.terms.export())
        {'keys': {'chat': 0, 'chien': 2, 'rat': 1}, 'tf': [1, 5, 2]}
        """
        data = {}
        data["keys"] = dict( zip(self.keys(), range(len(self))) )
        # each attr
        for name in self._attrs.keys():
            data[name] = self.get_attribute(name).export()
        return data

    def add(self, key, **kwargs):
        """ Add a key to the vector, do nothing if the key is already present
        
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, attrs={'tf': Numeric(default=1, min=0)}) 
        >>> doc.terms.add('chat')
        >>> doc.terms.add('dog', tf=2)
        >>> doc.terms.tf.values()
        [1, 2]
        
        >>> doc.terms.add('mouse', comment="a small mouse")
        Traceback (most recent call last):
        ...
        ValueError: Invalid attribute name: 'comment'
        
        >>> doc.terms.add('mouse', tf=-2)
        Traceback (most recent call last):
        ValidationError: ['Ensure this value ("-2") is greater than or equal to 0.']
        """
        if not self.has(key):
            # check if kwargs are valid
            for attr_name, value in six.iteritems(kwargs):
                if attr_name not in self._ftype.attrs:
                    raise ValueError("Invalid attribute name: '%s'" % attr_name)
                self._ftype.attrs[attr_name].validate(value)
            # add the key
            self._keys[key] = len(self._keys)
            # append attributes
            for name, attr_type in six.iteritems(self._ftype.attrs):
                attr_field = DocField.FromType(attr_type)
                if name in kwargs:
                    attr_field.set(kwargs[name])
                self._attrs[name].append(attr_field)

    def set(self, keys):
        """ Set new keys.
        Mind this will clear all attributes and keys before adding new keys
        
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, attrs={'tf': Numeric(default=1)}) 
        >>> doc.terms.add('copmputer', tf=12)
        >>> doc.terms.tf.values()
        [12]
        >>> doc.terms.set(['keyboard', 'mouse'])
        >>> list(doc.terms)
        ['keyboard', 'mouse']
        >>> doc.terms.tf.values()
        [1, 1]
        """
        # clear keys and atributes
        self._keys = OrderedDict()
        self.clear_attributes()
        _validate = self._ftype.validate
        for key in keys:
            self.add(_validate(key))

    def get_attr_value(self, key, attr):
        """ returns the value of a given attribute for a given key
        
        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, uniq=True, attrs={'tf': Numeric()}) 
        >>> doc.terms.add('chat', tf=55)
        >>> doc.terms.get_attr_value('chat', 'tf')
        55
        """
        idx = self._keys[key]
        return self._attrs[attr][idx].get_value()

    def set_attr_value(self, key, attr, value):
        """ set the value of a given attribute for a given key
        """
        idx = self._keys[key]
        self._attrs[attr][idx].set(value)

    def __getattr__(self, name):
        """ Returns the :class:`VectorAttr`

        :param name: attribute name
        :type name: str

        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, attrs={'tf': Numeric(default=1)}) 
        >>> doc.terms.add('computer', tf=12)
        >>> type(doc.terms.tf)
        <class 'reliure.schema.VectorAttr'>
        """
        if name in self._attrs: 
            return VectorAttr(self, name)
        else:
            raise SchemaError("No such attribute '%s' in Vector" % name)

    def __setattr__(self, name, values):
        """ Set all the attributes value

        >>> doc = Doc(docnum='1')
        >>> doc.terms = Text(multi=True, attrs={'tf': Numeric(default=1)}) 
        >>> doc.terms.add('computer', tf=12)
        >>> doc.terms.add('pad', tf=2)
        >>> doc.terms.tf = [3, 10]
        >>> doc.terms['computer'].tf
        3
        >>> doc.terms['pad'].tf
        10
        """
        if name.startswith('_'):
            DocField.__setattr__(self, name, values)
            #self.__dict__[attr] = value
        elif name in self.__dict__['_attrs']:
            if len(values) != len(self):
                raise SchemaError('Wrong size : |values| (=%s) should be equals to |keys| (=%s) ' \
                        % (len(values), len(self)))
            _attr = [DocField.FromType(self._ftype.attrs[name]) for _ in range(len(values)) ]
            for idx, val in enumerate(values):
                _attr[idx].set(val)
            self._attrs[name] = _attr
        else:
            raise SchemaError("No such attribute '%s' in Vector" % name)


class VectorAttr(object):
    """ Internal class used to acces an attribute of a :class:`.VectorField`

    >>> from reliure.types import Text, Numeric
    >>> doc = Doc(docnum='1')
    >>> doc.terms = Text(multi=True, uniq=True, attrs={'tf': Numeric()}) 
    >>> doc.terms.add('chat')
    >>> type(doc.terms.tf)
    <class 'reliure.schema.VectorAttr'>
    """
    #XXX; maybe it can be a "list" or a collections.Sequence
    # http://docs.python.org/2/library/collections.html#collections-abstract-base-classes

    def __init__(self, vector, attr):
        self.vector = vector
        self.attr = attr

    def __iter__(self):
        return (attr_value.get_value() for attr_value in self.vector._attrs[self.attr] if attr_value is not None)

    def values(self):
        # should we use doc.terms.tf() ??? 
        return list(self)

    def export(self):
        return [attr_value.export() for attr_value in self.vector._attrs[self.attr] if attr_value is not None]

    def __getitem__(self, idx_or_slice):
        if isinstance(idx_or_slice, slice):
            sl = idx_or_slice
            vector, attr = self.vector, self.attr
            return [attr_value.get_value() for attr_value in vector._attrs[attr][sl] if attr_value is not None]
        else:
            idx = idx_or_slice
            return self.vector._attrs[self.attr][idx].get_value()

    def __setitem__(self, idx, value):
        self.vector._attrs[self.attr][idx].set(value)


class VectorItem(object):
    """ Internal class used to acces an item (= a value) of a :class:`.VectorField`

    >>> from reliure.types import Text, Numeric
    >>> doc = Doc(docnum='1')
    >>> doc.terms = Text(multi=True, uniq=True, attrs={'tf': Numeric()}) 
    >>> doc.terms.add('chat')
    >>> type(doc.terms['chat'])
    <class 'reliure.schema.VectorItem'>
    """
    def __init__(self, vector, key):
        self._vector = vector
        self._key = key

    def attribute_names(self):
        return self._vector.attribute_names()

    def as_dict(self):
        return { k: self[k] for k in self.attribute_names() }
        
    def __getattr__(self, attr_name):
        return self._vector.get_attr_value(self._key, attr_name)

    def __setitem__(self, attr, value):
        setattr(self, attr, value)

    def __setattr__(self, attr, value):
        if not(attr.startswith('_')):
            self._vector.set_attr_value(self._key, attr, value)
        else: 
            object.__setattr__(self, attr, value)

    def __getitem__(self, name ):
        return getattr(self, name)


class Doc(dict):
    """ Cello Document object
    
    Here is an exemple of document construction from a simple text.
    First we define document's schema:
    
    >>> from reliure.types import Text, Numeric
    >>> term_field = Text(attrs={'tf':Numeric(default=1), 'positions':Numeric(multi=True)})
    >>> schema = Schema(docnum=Numeric(), text=Text(), terms=term_field)
    
    
    Now it is how one can build a document from this simple text:
    
    >>> text = \"\"\"i have seen chicken passing the street and i believed
    ... how many chicken must pass in the street before you
    ... believe\"\"\"
    
    Then we can create the document:

    >>> doc = Doc(schema, docnum=1, text=text)
    >>> doc.text[:6]
    'i have'
    >>> len(doc.text)
    113
    
    Then we can analyse the text:

    >>> tokens = text.split(' ')
    >>> from collections import OrderedDict
    >>> text_terms =  list(OrderedDict.fromkeys(tokens))
    >>> terms_tf = [ tokens.count(k) for k in text_terms ]
    >>> terms_pos = [[i for i, tok in enumerate(tokens) if tok == k ] for k in text_terms]

    .. note:: there is better way to analyse a text with Cello !
    
    and one can store the result in the field "terms":
    
    >>> doc.terms = text_terms
    >>> doc.terms.tf.values()   # here we got only '1', it's the default value
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    >>> doc.terms.tf = terms_tf
    >>> doc.terms.positions = terms_pos

    One can access the information, for example, for the term "chicken":
    
    >>> key = "chicken"
    >>> doc.terms[key].tf
    2
    >>> doc.terms[key].positions
    [3, 11]
    >>> doc.terms.get_attr_value(key, 'positions')
    [3, 11]
    >>> doc.terms._keys[key]
    3
    >>> doc.terms.positions[3]
    [3, 11]
    
    
    #TODO: docnum doit etre un field spécial
    #TODO: la valeur de docnum doit être passer en argument de __init__
    """
    
    def __str__(self):
        return "<%s %s %s>" % (self.__class__.__name__, self.schema,
            { k: self[k] for k in self.schema.field_names() }
        )

    def __init__(self, schema=None, **data):
        """ Document initialisation
        
        .. warning:: a copy of the given schema is stored in the document
        
        Simple exemple:
        
        >>> from reliure.types import Text, Numeric
        >>> doc = Doc(Schema(titre=Text()), titre='Un titre')
        """
        dict.__init__(self)

        if schema is None:
            schema = Schema()
        else:
            schema = schema.copy()
        object.__setattr__(self, 'schema', schema)

        # fields value(s)
        for key, ftype in schema.iter_fields():
            self[key] = DocField.FromType(ftype)
            if key in data:
                self.set_field(key,data[key])

    def add_field(self, name, ftype, docfield=None):
        """ Add a field to the document (and to the underlying schema)
        
        :param name: name of the new field
        :type name: str
        :param ftype: type of the new field
        :type ftype: subclass of :class:`.GenericType`
        """
        self.schema.add_field(name, ftype)
        self[name] = docfield or DocField.FromType(ftype)

    def get_field(self, name):
        """ return the :class:`DocField` field for the given name """
        try:
            return dict.__getitem__(self, name)
        except KeyError as err:
            raise SchemaError("'%s' is not a document field (existing attributes are: %s)" % (err, list(self)))

    def set_field(self, name, value, parse=False):
        """ set field """
        # explicit getitem needed for ValueField
        try: 
            item = dict.__getitem__(self, name)
            item.set( item.parse(value) if parse else value  )
        except ValidationError as err:
            raise FieldValidationError(name, value, list(err))
            
    def __getitem__(self, name):
        return getattr(self, name)

    def __getattr__(self, name):
        """ Return a value if the type of the :class:`DocField` is instance of
        :class:`ValueField`
        prefer :func:`get_field` is you want direct acces to the container.
        """
        # this is called if there is no 'real' object attribute of the given name
        # http://docs.python.org/2/reference/datamodel.html#object.__getattr__s
        field = self.get_field(name)
        if type(field) == ValueField:
            return field.get_value()
        else:
            return field

    def __setitem__(self,name, value):
        setattr(self, name, value)

    def __setattr__(self, name, value):
        if name == 'schema':
            raise SchemaError("Impossible to replace the schema of a document")
        elif isinstance(value, GenericType):
            # the value is a "Type" => creation of a new attribute
            self.add_field(name, value)
        elif isinstance(value, DocField):
            # the new value is a 'Field', we just add it
            dict.__setitem__(self, name, value)
        elif name in self.schema.field_names():
            # set a value to one field
            self.set_field(name, value)
        else:
            raise SchemaError("'%s' is not a document field (existing attributes are: %s)" % (name, list(self)))

    def export(self, exclude=[]):
        """ returns a dictionary representation of the document
        """
        fields = ( (key, self.get_field(key)) for key in self.schema
            if not key.startswith("_") and key not in exclude )
        
        doc = {name: field.export() for name, field in fields}
        return doc

