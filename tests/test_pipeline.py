#-*- coding:utf-8 -*-
import unittest

from datetime import datetime

from reliure.exceptions import ValidationError
from reliure.types import GenericType, Numeric, Text, Boolean
from reliure.pipeline import Composable, Optionable, OptionableSequence, Pipeline


class TestComposable(unittest.TestCase):
    def testRaises(self):
        comp = Composable()
        with self.assertRaises(NotImplementedError):
            comp()
        fct = 12
        with self.assertRaises(ValueError):
            pl = comp | fct

    def testNames(self):
        def fct(x):
            return x
        comp = Composable(fct)
        self.assertEqual(comp.name, "fct")
        comp = Composable(fct, name="autre")
        self.assertEqual(comp.name, "autre")

        opt = Optionable()
        self.assertEqual(opt.name, "Optionable")


class MyOptionable(Optionable):
    def __init__(self):
        super(MyOptionable, self).__init__("testOptionableName")
        self.add_option("alpha", Numeric(default=4, min=1, max=20))
        self.add_option("name", Text(default=u"un", choices=[u"un", u"deux"]))

    @Optionable.check
    def __call__(self, alpha=None, name=None):
        return alpha, name

# this should work without a check BUT should be avoided
class MyOptionableNoCheck(Optionable):
    def __init__(self):
        super(MyOptionableNoCheck, self).__init__("testOptionableNameNoCheck")
        self.add_option("name", Text(default=u"un", choices=[u"un", u"deux"]))

    def __call__(self, name=None):
        return 2, name


class TestOptionable(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        pass

    def testOptionableName(self):
        comp = Optionable("composant")
        self.assertEqual(comp.name, "composant")
        comp.name = "nouveau_nom"
        self.assertEqual(comp.name, "nouveau_nom")
        with self.assertRaises(ValueError):
            comp.name = "nouveau nom"

    def testCheckDecorator(self):
        comp = MyOptionable()
        # should be able to run without outparamters
        alpha, name = comp()
        self.assertEqual(alpha, 4)
        self.assertEqual(name, u"un")
        alpha, name = comp(alpha=2, name=u"deux")
        self.assertEqual(alpha, 2)
        self.assertEqual(name, u"deux")
        with self.assertRaises(ValueError):
            alpha, name = comp(beta=2)
        comp.force_option_value("alpha", 10)
        with self.assertRaises(ValueError):
            alpha, name = comp(alpha=5)
        alpha, name = comp()
        self.assertEqual(alpha, 10)

    def testCheckDecoratorFlag(self):
        comp = MyOptionable()
        # should kave a "_checked" flag
        self.assertTrue(hasattr(comp.__call__, "_checked"))
        # that should be true
        self.assertTrue(comp.__call__._checked)
        # but not if @check is not make (that is not good...)
        comp = MyOptionableNoCheck()
        self.assertFalse(hasattr(comp.__call__, "_checked"))
        

    def testAddOption(self):
        comp = Optionable("composant")
        comp.add_option("alpha", Numeric())
        self.assertTrue("alpha" in comp.get_options())
        comp.add_option("beta", Numeric(), hidden=True)
        self.assertFalse("beta" in comp.get_options())

        with self.assertRaises(ValueError):
            comp.add_option("alpha", Numeric())

        with self.assertRaises(ValueError):
            comp.add_option("alpha beta", Numeric())

        # for now, no vector value
        with self.assertRaises(NotImplementedError):
            comp.add_option("gamma", Numeric(uniq=True))
        # for now, no attribut value
        with self.assertRaises(NotImplementedError):
            comp.add_option("gamma", Numeric(attrs={"a": Numeric()}))

    def testGetSetOption(self):
        comp = Optionable("composant")
        comp.add_option("alpha", Numeric(
                help="A short description",
                default=2,
                vtype=int,
                min=0,
                max=4,
            )
        )
        comp.add_option("name", Text(
                help="A text ?",
                default=u"chat"
            )
        )
        # value
        self.assertEquals(comp.get_option_value("alpha"), 2)
        with self.assertRaises(ValueError):
            comp.set_option_value("gamma", 10)
        with self.assertRaises(ValueError):
            val = comp.get_option_value("gamma")
        with self.assertRaises(ValidationError):
            comp.set_option_value("alpha", -1)
        with self.assertRaises(ValidationError):
            comp.set_option_value("alpha", 3.21)
        comp.set_option_value("alpha", 0)
        self.assertEquals(comp.get_option_value("alpha"), 0)
        comp.set_option_value("alpha", "4", parse=True)
        self.assertEquals(comp.get_option_value("alpha"), 4)
        # value set for text
        self.assertEquals(comp.get_option_value("name"), u"chat")
        comp.set_option_value("name", "chien", parse=True)
        self.assertEquals(comp.get_option_value("name"), u"chien")

        # default value
        self.assertEquals(comp.get_option_default("alpha"), 2)
        with self.assertRaises(ValidationError):
            comp.change_option_default("alpha", 55)
        with self.assertRaises(ValueError):
            comp.change_option_default("gamma", 55)
        with self.assertRaises(ValueError):
            comp.get_option_default("gamma")
        comp.change_option_default("alpha", 1)
        self.assertEquals(comp.get_option_default("alpha"), 1)

        # force option value
        with self.assertRaises(ValueError):
            comp.force_option_value("gamma", 55)
        comp.force_option_value("alpha", 4)
        self.assertTrue(comp.option_is_hidden("alpha"))
        self.assertEquals(comp.get_option_value("alpha"), 4)
        self.assertEquals(comp.get_option_default("alpha"), 4)

        # test clear options values
        self.assertEquals(comp.get_option_value("name"), u"chien")
        comp.clear_option_value("name")
        self.assertEquals(comp.get_option_value("name"), u"chat")
        comp.set_option_value("name", "chien", parse=True)
        comp.clear_options_values()
        self.assertEquals(comp.get_option_value("name"), u"chat")

    def testBooleanOption(self):
        comp = Optionable("composant")
        comp.add_option("filtering", Boolean(default=True, help="whether to activate a funcky filter !"))
        self.assertDictEqual(comp.get_options(), {
            'filtering': {
                    'name': 'filtering',
                    'value': True,
                    'type': 'value',
                    'otype': {
                        'type': 'Boolean',
                        'default': True,
                        'choices': None,
                        'multi': False,
                        'uniq': False,
                        'help': 'whether to activate a funcky filter !',
                    }
                }
        })
        comp.force_option_value("filtering", False)
        self.assertDictEqual(comp.get_options(), {})
        with self.assertRaises(ValueError):
            comp.set_option_value("filtering", True)

class TestOptionableSequence(unittest.TestCase):
    def testNoOptions(self):
        def f1(x):
            return x**2
        def f2(x):
            return x+2
        comp = OptionableSequence(f1, f2)
        with self.assertRaises(NotImplementedError):
            comp()
        self.assertEquals(repr(comp), "OptionableSequence(Composable(f1), Composable(f2))")
        self.assertEquals(comp.name, "f1+f2")
        self.assertEquals(comp[0].name, "f1")
        self.assertEquals(len(comp), 2)
        comp.close()

    def testOptions(self):
        opt = MyOptionable()
        opt2 = Optionable("opt2")
        opt2.add_option("filtering", Boolean(default=True, help="whether to activate a funcky filter !"))
        with self.assertRaises(AssertionError):
            OptionableSequence(opt, opt)
        comp = OptionableSequence(opt, opt2)
        self.assertTrue(comp.has_option("filtering"))
        comp.set_option_value("filtering", False)
        self.assertFalse(comp.get_option_value("filtering"))
        with self.assertRaises(ValueError):
            comp.set_option_value("FFfiltering", False)
        self.assertEquals(comp.get_option_default("filtering"), True)
        comp.change_option_default("filtering", False)
        self.assertEquals(comp.get_option_default("filtering"), False)
        # hidden or not
        self.assertFalse(comp.option_is_hidden("alpha"))
        self.assertFalse(comp.option_is_hidden("name"))
        self.assertEquals(comp.get_option_default("name"), u"un")
        comp.force_option_value("name", u"deux")
        self.assertEquals(comp.get_option_default("name"), u"deux")
        self.assertTrue(comp.option_is_hidden("name"))
        # bulk set
        with self.assertRaises(ValueError):
            vals = {
                "name": "deux",
            }
            comp.set_options_values(vals, parse=True, strict=True)
        with self.assertRaises(ValueError):
            vals = {
                "forname": "deux",
            }
            comp.set_options_values(vals, parse=True, strict=True)
        vals = {
            "filtering": "False",
            "alpha": "3"
        }
        comp.set_options_values(vals, parse=True, strict=True)
        self.assertDictEqual(comp.get_options_values(hidden=True), {
            "filtering": False,
            "name": u"deux",
            "alpha": 3
        })
        self.assertDictEqual(comp.get_options_values(hidden=False), {
            "filtering": False,
            "alpha": 3
        })
        # get otpions
        self.assertListEqual(comp.get_ordered_options(),
            [
                {
                    'name': 'alpha',
                    'otype': {
                        'vtype': 'int',
                        'default': 4,
                        'multi': False,
                        'uniq': False,
                        'choices': None,
                        'help': '',
                        'max': 20,
                        'min': 1,
                        'type': 'Numeric',
                    },
                    'type': 'value',
                    'value': 3
                },
                {
                    'name': 'filtering',
                    'otype': {
                        'choices': None,
                        'default': False,
                        'help': 'whether to activate a funcky filter !',
                        'multi': False,
                        'type': 'Boolean',
                        'uniq': False
                    },
                    'type': 'value',
                    'value': False
                }
            ]
        )
