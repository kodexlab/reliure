#-*- coding:utf-8 -*-
import unittest
import cello

from datetime import datetime
from reliure.exceptions import ReliureTypeError, ValidationError
from reliure.types import GenericType, Numeric, Text, Boolean, Datetime

class TestFieldTypes(unittest.TestCase):
    def setUp(self):
        pass

    def test_generic_type(self):
        f = GenericType()
        self.assertEqual(f.validate("45"), "45")
        self.assertEqual(f.validate(45), 45)
        self.assertEqual(f.validate(str), str)
        
        self.assertEqual(f.parse("45"), "45")

        # test invalid arguments
        with self.assertRaises(ReliureTypeError):
            f = GenericType(uniq=False, attrs={"score":Numeric()})
        with self.assertRaises(ReliureTypeError):
            f = GenericType(multi=False, attrs={"score":Numeric()})
        with self.assertRaises(ReliureTypeError):
            f = GenericType(uniq=True, multi=False)

    def test_numeric(self):
        # Numeric Field (int or float)
        f = Numeric(vtype=float)
        self.assertNotEqual(repr(f), "")
        self.assertRaises(ReliureTypeError, lambda: Numeric(vtype=any) )
        self.assertEqual(f.validate(2.), 2.)  # ok
        self.assertEqual(f.validate(-2.2), -2.2)  # ok
        self.assertEqual(f.validate(-5e0), -5.)  # ok
        self.assertEqual(f.validate(0.), 0.)  # ok
        self.assertRaises(ValidationError, f.validate, 1)
        self.assertRaises(ValidationError, f.validate, "1")
        self.assertRaises(ValidationError, f.validate, "blabla")
        self.assertRaises(ValidationError, f.validate, int)
        
        self.assertEqual(f.parse("45"), 45.)

        # unsigned field
        f = Numeric(vtype=int, min=0)
        self.assertEqual(f.validate(2), 2)  # ok
        self.assertEqual(f.validate(0), 0)  # ok
        self.assertRaises(ValidationError, f.validate, -1)
        
        self.assertEqual(f.parse("45"), 45)
        
        # with min and max
        f = Numeric(vtype=int, min=-10, max=45)
        self.assertEqual(f.validate(-10), -10)  # ok
        self.assertEqual(f.validate(0), 0)  # ok
        self.assertEqual(f.validate(2), 2)  # ok
        self.assertEqual(f.validate(45), 45)  # ok
        self.assertRaises(ValidationError, f.validate, -45)
        self.assertRaises(ValidationError, f.validate, 4.5)
        self.assertRaises(ValidationError, f.validate, -11)
        self.assertRaises(ValidationError, f.validate, 55)
        
        # with min and max
        f = Numeric(vtype=int, min=0, max=4, help="an int")
        self.assertEqual(f.validate(0), 0)  # ok
        self.assertEqual(f.validate(4), 4)  # ok
        self.assertRaises(ValidationError, f.validate, -1)
        self.assertRaises(ValidationError, f.validate, 8)
        
        # as dict
        self.assertDictEqual(f.as_dict(), {
                        'vtype': 'int',
                        'default': None,
                        'multi': False,
                        'uniq': False,
                        'choices': None,
                        'help': 'an int',
                        'max': 4,
                        'min': 0,
                        'type': 'Numeric',
            }
        )

    def test_text(self):
        # setting wrong types 
        self.assertRaises(ReliureTypeError, lambda: Text(vtype=any))
        
        # check unicode
        f_unicode = Text(vtype=unicode)
        self.assertNotEqual(repr(f_unicode), "")
        # good type
        self.assertEqual(f_unicode.validate(u"boé"), u'boé')
        self.assertRaises(ValidationError, f_unicode.validate, "boo")
        self.assertRaises(ValidationError, f_unicode.validate, 1)
        
        self.assertEqual(f_unicode.parse("boé"), u'boé')
        self.assertEqual(f_unicode.parse(u"boé"), u'boé')

        # check str
        f_str = Text(vtype=str)
        self.assertNotEqual(repr(f_str), "")
        # good type
        self.assertEqual(f_str.validate("boé"), 'boé')
        self.assertRaises(ValidationError, f_str.validate, u"boo")
        self.assertRaises(ValidationError, f_str.validate, 1)

        self.assertEqual(f_str.parse("boé"), 'boé')
        self.assertEqual(f_str.parse(u"boé"), 'boé')


    def test_choices(self):
        with self.assertRaises(ValidationError):
            choice = Text(vtype=str, default="a", choices=["b", "c", "d"])
        with self.assertRaises(ValidationError):
            #unicode needed
            choice = Text(default="a", choices=["a", "b", "c", "d"])
        choice = Text(default=u"a", choices=[u"a", u"b", u"c", u"d"])
        with self.assertRaises(ValidationError):
            choice.default = u"e"
        with self.assertRaises(ValidationError):
            choice.default = "a"
        choice.default = u"c"
        self.assertEqual(choice.default, u"c")
        
        # validate
        self.assertEqual(choice.validate(u"a"), u"a")
        self.assertRaises(ValidationError, choice.validate, u"h")

        # parse
        self.assertEqual(choice.parse("a"), "a")
        with self.assertRaises(ValidationError):
            choice.parse("fr")
        with self.assertRaises(ValidationError):
            choice.parse("f")

    def test_boolean(self):
        tbool = Boolean()
        self.assertEqual(tbool.validate(True), True)
        self.assertEqual(tbool.validate(False), False)
        self.assertRaises(ValidationError, tbool.validate, 1)
        self.assertRaises(ValidationError, tbool.validate, "oui")
        
        self.assertEqual(tbool.parse("1"), True)
        self.assertEqual(tbool.parse("yes"), True)
        self.assertEqual(tbool.parse("True"), True)
        self.assertEqual(tbool.parse(u"true"), True)
        self.assertEqual(tbool.parse(u"TRUE"), True)
        self.assertEqual(tbool.parse(u"true"), True)
        self.assertEqual(tbool.parse("oui"), True)
        self.assertEqual(tbool.parse(u"0"), False)
        self.assertEqual(tbool.parse(u"false"), False)
        self.assertEqual(tbool.parse(u"faux"), False)
        self.assertEqual(tbool.parse(u"qsdqsdf"), False)

    def test_datetime(self):
        f = Datetime()
        self.assertRaises(ValidationError, f.validate, "45")
        self.assertEqual(f.validate(datetime(year=2013, month=11, day=4)), \
                datetime(year=2013, month=11, day=4))
        # as dict
        self.assertDictEqual(f.as_dict(), {
                        'type': 'Datetime',
                        'choices': None,
                        'default': None,
                        'help': '',
                        'multi': False,
                        'uniq': False,
            }
        )


