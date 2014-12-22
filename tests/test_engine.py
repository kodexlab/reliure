#-*- coding:utf-8 -*-
import unittest

from cello.exceptions import CelloError
from cello.types import Numeric
from cello.pipeline import Composable, Optionable
from cello.engine import Block, Engine

# We create some simple components used to test Block and Engine

class OptProductEx(Optionable):
    def __init__(self):
        super(OptProductEx, self).__init__("mult_opt")
        self.add_option("factor", Numeric(default=5, help="multipliation factor", vtype=int))

    @Optionable.check
    def __call__(self, arg, factor=None):
        return arg * factor

# same component than OptProductEx except that the call is not decoreted by a check
class OptProductExNoCheck(Optionable):
    def __init__(self):
        super(OptProductExNoCheck, self).__init__("mult_opt")
        self.add_option("factor", Numeric(default=5, help="multipliation factor", vtype=int))

    def __call__(self, arg, factor=5):
        return arg * factor

class CompAddTwoExample(Composable):
    def __init__(self):
        Composable.__init__(self, name="plus_comp")

    def __call__(self, arg):
        return arg + 2


class MinusTwoInputs(Composable):
    def __init__(self):
        Composable.__init__(self, name="minus_comp")

    def __call__(self, left, right):
        return left - right


# ok let's tests start !

class TestBlock(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        # setup 3 components
        self.mult_opt = OptProductEx()
        self.plus_comp = CompAddTwoExample()
        def max20(arg):
            return min(arg, 20)
        self.max_comp = Composable(max20)

    def test_comp(self):
        self.assertEquals(self.mult_opt(0), 0)
        self.assertEquals(self.mult_opt(3), 15)
        self.assertEquals(self.plus_comp(3), 5)
        self.assertEquals(self.plus_comp(3), 5)
        self.assertEquals(self.max_comp(3), 3)
        self.assertEquals(self.max_comp(300), 20)

    def test_init(self):
        with self.assertRaises(ValueError):
            block = Block("foo with space")
        with self.assertRaises(ValueError):
            block = Block(24)
        # good name
        block = Block("foo")
        self.assertListEqual(block.component_names(), [])
        self.assertListEqual(block.selected(), [])

    def test_append(self):
        block = Block("foo")
        # it should be possible to add a Composable
        block.append(self.mult_opt)
        # but not possible to add it two times
        with self.assertRaises(ValueError):
            block.append(self.mult_opt)
        # possible to add directly a lambda
        block.append(lambda x: x)
        # but not a not callable
        with self.assertRaises(ValueError):
            block.append(2)
        block.append(self.plus_comp, default=True)
        block.append(self.max_comp)
        self.assertListEqual(block.component_names(), ['mult_opt', '<lambda>', 'plus_comp', 'max20'])
        self.assertListEqual(block.selected(), ['plus_comp'])
        self.assertListEqual(block.defaults, ["plus_comp"])
        self.assertEquals(len(block), 4)
        self.assertDictEqual(block.as_dict(), {
            'name': 'foo',
            'args': None,
            'returns': 'foo',
            'multiple': False,
            'required': True,
            'components': [
                {
                    'name': 'mult_opt',
                    'default': False,
                    'options': [
                        {
                            'name': 'factor',
                            'otype': {
                                'choices': None,
                                'default': 5,
                                'help': 'multipliation factor',
                                'max': None,
                                'min': None,
                                'multi': False,
                                'type': 'Numeric',
                                'uniq': False,
                                'vtype': 'int'
                            },
                            'type': 'value',
                            'value': 5
                        }
                    ]
                },
                {'default': False, 'name': '<lambda>', 'options': None},
                {
                    'name': 'plus_comp',
                    'default': True,
                    'options': None
                },
                {
                    'name': 'max20',
                    'default': False,
                    'options': None
                }
            ]
        })

    def test_select_and_clear_selection(self):
        ## select should permits to set options of blocks
        block = Block("foo")
        block.set(self.plus_comp, self.mult_opt)
        # should be required by default
        self.assertTrue(block.required)
        # so the 1st comp should be selected by default
        self.assertEqual(block.selected(), ['plus_comp'])   #first select by default
        self.assertEqual(block['mult_opt'].get_option_value("factor"), 5)  # default comp option value is 5
        # select the second comp
        block.select("mult_opt", options={"factor": 50})
        self.assertEqual(block.selected(), ['mult_opt'])
        self.assertEqual(block['mult_opt'].get_option_value("factor"), 50)

        ## clear selection 
        block.clear_selections()
        # we should be in intial state
        self.assertEqual(block.selected(), ['plus_comp'])   #first select by default
        self.assertEqual(block['mult_opt'].get_option_value("factor"), 5)  # default comp option value is 5

        ## default should imply select if block required
        block.setup(defaults="mult_opt")
        self.assertListEqual(block.defaults, ["mult_opt"])
        self.assertListEqual(block.selected(), ["mult_opt"])

        ## default should NOT imply select if block not required
        block.setup(required=False)
        self.assertListEqual(block.defaults, ["mult_opt"])
        self.assertListEqual(block.selected(), [])

    def test_play(self):
        block = Block("foo")
        block.set(self.mult_opt, self.plus_comp, self.max_comp)
        # Should use the first comp by default
        self.assertListEqual(block.defaults, ["mult_opt"])
        self.assertListEqual(block.selected(), ["mult_opt"])
        self.assertEquals(block.play(3), 15)
        self.assertTrue(block.meta.time > 0)

        # may be not required then play return None if no selected components
        block.setup(required=False)
        self.assertListEqual(block.selected(), [])
        self.assertListEqual(block.defaults, [])
        self.assertEqual(block.play(3), None)

        # default
        block.select("plus_comp")
        self.assertListEqual(block.selected(), ["plus_comp"])
        self.assertEquals(block.play(3), 5)
        
        # test select
        with self.assertRaises(ValueError):
            block.select("donotexist")
        block.select("max20")
        self.assertListEqual(block.selected(), ['max20'])

        # test run
        self.assertEquals(block.play(3), 3)
        self.assertEquals(block.play(50), 20)

        # test select with option
        block.select("mult_opt", options={'factor':21})
        self.assertListEqual(block.selected(), ['mult_opt'])
        with self.assertRaises(ValueError):
            block.select("max20", options={'factor':21})

        # test run
        self.assertEquals(block.play(10), 210)
        self.assertEquals(block.play(0), 0)
        # run a la main
        # it should keep the option value setted before
        self.assertEquals(block['mult_opt'](1), 21)
        # but it could be possible to force it
        self.assertEquals(block['mult_opt'](1, factor=11), 11)

    def test_play_force_option(self):
        # block should work with a option forced to a special value
        comp = OptProductEx()
        comp.force_option_value("factor", 4)
        block = Block("foo")
        block.set(comp)
        res = block.play(10)
        self.assertEquals(res, 40)

    def test_play_force_option_without_check(self):
        # block should work with a option forced to a special value EVEN when the call is not "checked"
        comp = OptProductExNoCheck()
        comp.force_option_value("factor", 4)
        block = Block("foo")
        block.set(comp)
        res = block.play(10)
        self.assertEquals(res, 40)

    def test_set_options(self):
        block = Block("foo")
        block.set(self.mult_opt, self.plus_comp, self.max_comp)
        # test set options
        block.setup(required=True)
        self.assertTrue(block.required)
        self.assertFalse(block.hidden)
        self.assertFalse(block.multiple)
        block.setup(required=False)
        self.assertFalse(block.required)
        block.setup(required=True, multiple=True, hidden=True)
        self.assertTrue(block.required)
        self.assertTrue(block.hidden)
        self.assertTrue(block.multiple)
        ## test input output names
        self.assertEquals(block.in_name, None)
        self.assertEquals(block.out_name, "foo")
        block.setup(in_name="doclist", out_name="graph")
        self.assertEquals(block.in_name, ["doclist"])
        self.assertEquals(block.out_name, "graph")

    def test_multiple_inputs(self):
        # block.play should work with coponents with mutliples in
        minus_comp = MinusTwoInputs()
        block = Block("foo")
        block.set(minus_comp)
        res = block.play(10, 3)
        self.assertEquals(res, 7)


class TestEngine(unittest.TestCase):
    maxDiff = None
    
    def setUp(self):
        # setup 3 components
        self.mult_opt = OptProductEx()
        self.plus_comp = CompAddTwoExample()
        def max20(arg):
            return min(arg, 20)
        self.max_comp = Composable(max20)

    def test_empty_engine(self):
        engine = Engine()
        # empty should not validate
        with self.assertRaises(CelloError):
            engine.validate()
        # should not be possible to require some blocks...
        with self.assertRaises(ValueError):
            engine.requires()
        with self.assertRaises(ValueError):
            engine.requires("foo", "foo")

    def test_engine_default_pipeline(self):
        engine = Engine("op1", "op2", "op3")
        # should have a __len__
        self.assertEqual(len(engine), 3)
        # should have a __contains__
        self.assertTrue("op1" in engine)
        self.assertTrue("op2" in engine)
        self.assertTrue("op3" in engine)
        self.assertFalse("op4" in engine)
        # should not be possible to require a block that do not exist
        with self.assertRaises(CelloError):
            engine.requires("op4")
        # should be possible to set the component for each block
        engine.op1.set(self.mult_opt)
        # but not on non existing blocks 
        with self.assertRaises(ValueError):
            engine.op4.set(self.mult_opt)
        with self.assertRaises(ValueError):
            engine["op4"].set(self.mult_opt)
        with self.assertRaises(ValueError):
            engine.set("op4", self.mult_opt)
        
        # should not validate if there is no component for all blocks
        with self.assertRaises(CelloError):
            engine.validate()

        #should be posisble to 'append' a possible component to the block
        engine.op2.append(self.mult_opt)
        # and to set is as default in the same time
        engine.op2.append(self.plus_comp, default=True)
        
        # should be possible to select on component
        engine.op1.select("mult_opt")

        # should be possible to know if one block is multiple
        self.assertFalse(engine.op2.multiple)
        # to know wich component will be run
        self.assertEqual(engine.op2.selected(), ["plus_comp"])
        # to play just one block !
        self.assertEqual(engine.op2.play(10), 12)

        # and then is should validate is every block has som components
        engine.set("op3", self.mult_opt, self.plus_comp, self.max_comp)
        engine.validate()

        # should play !
        res = engine.play(3) # mult * 5 | + 2 | mult
        # and all intermediare results should be available
        self.assertEquals(res['input'], 3)
        self.assertEquals(res['op1'], 3*5)
        self.assertEquals(res['op2'], 3*5+2)
        self.assertEquals(res['op3'], (3*5+2)*5)

    def test_as_dict(self):
        engine = Engine("op1", "op2")
        engine.set("op1", self.plus_comp, self.mult_opt, self.max_comp)
        engine.set("op2", self.plus_comp)
        self.assertDictEqual(engine.as_dict(), {
            'args': ['input'],
            'blocks': [
                {
                    'components': [
                        {
                            'default': True,       #This is the default NOT the selected value
                            'name': 'plus_comp',
                            'options': None
                        },
                        {
                            'default': False,
                            'name': 'mult_opt',
                            'options': [
                                {
                                    'name': 'factor',
                                    'type': 'value',
                                    'value': 5,
                                    'otype': {
                                        'choices': None,
                                        'default': 5,
                                        'help': 'multipliation factor',
                                        'max': None,
                                        'min': None,
                                        'multi': False,
                                        'type': 'Numeric',
                                        'uniq': False,
                                        'vtype': 'int'
                                    }
                               }
                            ]
                        },
                        {
                            'name': 'max20',
                            'default': False,
                            'options': None
                        }
                    ],
                     'args': None,
                     'multiple': False,
                     'name': 'op1',
                     'returns': 'op1',
                     'required': True
                },
                {
                    'components': [
                         {
                             'name': 'plus_comp',
                             'default': True,
                             'options': None
                         }
                     ],
                     'args': None,
                     'multiple': False,
                     'name': 'op2',
                     'returns': 'op2',
                     'required': True
                 }
            ]
        })

    def test_configure(self):
        engine = Engine("op1", "op2")
        engine.set("op1", self.plus_comp, self.mult_opt, self.max_comp)
        engine.set("op2", self.plus_comp)

        self.assertEqual(engine.op1["mult_opt"].get_option_value("factor"), 5)
        engine.configure({
            'op1':{
                'name': 'mult_opt',
                'options': {
                    'factor': '10'
                }
            },
            'op2':{
                'name': 'plus_comp'
            }
        })
        self.assertEqual(engine.op1.selected(), ["mult_opt"])
        self.assertEqual(engine.op1["mult_opt"].get_option_value("factor"), 10)
        self.assertEqual(engine.op1.play(5), 50)
        
        # A new call to configure should reset the default values
        engine.configure({})    #this should reset the selected/options to default state
        self.assertEqual(engine.op1.selected(), ["plus_comp"])
        self.assertEqual(engine.op1["mult_opt"].get_option_value("factor"), 5)

    def test_configure_errors(self):
        # Should raise valueError when configuration is not valit
        engine = Engine("op1", "op2", "op3")
        engine.set("op1", self.mult_opt, self.plus_comp, self.max_comp)
        engine.set("op2", self.plus_comp, self.mult_opt, self.max_comp)
        engine.op2.setup(hidden=True)
        engine.set("op3", self.mult_opt, self.plus_comp, self.max_comp)

        with self.assertRaises(ValueError): # op2 hidden it can be configured
            engine.configure({
                'op2':{'name': 'max20'}
            })
        with self.assertRaises(ValueError): # 'maxmax' doesn't exist
            engine.configure({
                'op3':{'name': 'maxmax'}
            })
        with self.assertRaises(ValueError): # error in op1 format
            engine.configure({
                'op1':{'namss': 'mult'}
            })
        with self.assertRaises(ValueError): # block doesn't exist
            engine.configure({
                'op5':{'name': 'max20'}
            })
        with self.assertRaises(ValueError): # block required !
            engine.configure({
                'op1':[]
            })
        with self.assertRaises(ValueError): # block not multi !
            engine.configure({
                'op1':[{'name': 'max20'}, {'name': 'plus_comp'}]
            })

    def test_engine_named_inout_pipeline(self):
        engine = Engine("op1", "op2", "op3")
        
        engine.op1.set(self.mult_opt)
        engine.op1.setup(in_name="in1", out_name="out1")

        engine.op2.set(self.plus_comp)
        engine.op2.setup(in_name="out1", out_name="out2")

        engine.op3.set(self.mult_opt)
        engine.op3.setup(in_name="out2", out_name="out3")

        res = engine.play(3) # mult * 5 | + 2 | mult
        self.assertEquals(res['in1'], 3)
        self.assertEquals(res['out1'], 3*5)
        self.assertEquals(res['out2'], 3*5+2)
        self.assertEquals(res['out3'], (3*5+2)*5)

    def test_engine_named_inout_error(self):
        engine = Engine("op1", "op2", "op3")

        engine.op1.set(self.mult_opt)
        engine.op1.setup(in_name="in1", out_name="out1")

        engine.op2.set(self.plus_comp)
        engine.op2.setup(in_name="out_not_exist", out_name="out2")

        engine.op3.set(self.mult_opt)
        engine.op3.setup(in_name="out1", out_name="out3")

        with self.assertRaises(CelloError):
            engine.validate()
        
        engine.op2.setup(in_name="in1", out_name="out2")
        engine.validate()

        engine.op2.setup(required=False)
        engine.op3.setup(in_name="out2")
        with self.assertRaises(CelloError):
            engine.validate()

    def test_engine_named_inout_multiin(self):
        # a block should work with multiple inputs
        engine = Engine("op1", "op2", "op3")
        
        engine.op1.set(self.mult_opt)
        engine.op1.setup(in_name="in1", out_name="out1")
        engine.op2.set(self.plus_comp)
        engine.op2.setup(in_name="in1", out_name="out2")
        engine.op3.set(MinusTwoInputs())
        engine.op3.setup(in_name=["out1", "out2"], out_name="out3")

        res = engine.play(3) # (mult * 5) - (3 + 2)
        self.assertEquals(res['in1'], 3)
        self.assertEquals(res['out1'], 3*5)
        self.assertEquals(res['out2'], 3+2)
        self.assertEquals(res['out3'], (3*5) - (3+2))

        # it should be possible to have a multi in as first component !
        engine = Engine("op3")
        engine.op3.set(MinusTwoInputs())
        engine.op3.setup(in_name=["in1", "in2"], out_name="out")
        res = engine.play(3, 40)
        self.assertEquals(res['out'], -37)

        # it should not validate if multiple data are not present
        engine = Engine("op1", "op3")
        engine.op1.set(self.mult_opt)
        engine.op1.setup(in_name="in1", out_name="out1")
        engine.op3.set(MinusTwoInputs())
        engine.op3.setup(in_name=["out1", "out2"], out_name="out3")

        with self.assertRaises(CelloError):
            engine.validate()

    def test_engine_multi_entry_point(self):
        engine = Engine("op1", "op2")
        engine.op1.setup(in_name="in1", out_name="middle", required=False)
        engine.op2.setup(in_name="middle", out_name="out")
        engine.op1.append(self.mult_opt)
        engine.op2.append(self.plus_comp)

        # should run all the blocks
        engine.op1.select("mult_opt")
        res = engine.play(10)
        self.assertEquals(res["out"], 52)
        self.assertEquals(res["middle"], 50)
        # should be possible to named the input of the 1st block
        res = engine.play(in1=10)
        self.assertEquals(res["out"], 52)
        self.assertEquals(res["middle"], 50)

        # should need input 'in'
        with self.assertRaises(CelloError):
            res = engine.play(middle=10)

        # should not be possible to give to many inputs
        with self.assertRaises(CelloError):
            res = engine.play(middle=10, in1=10)

        # should be possible to not play the op1 block
        engine.op1.clear_selections()
        res = engine.play(middle=10)
        self.assertEquals(len(res), 2)
        self.assertEquals(res["middle"], 10)
        self.assertEquals(res["out"], 12)

    def test_engine_multi_entry(self):
        engine = Engine("op1", "op2")

        engine.op1.set(self.mult_opt)
        engine.op1.setup(in_name="in1", out_name="middle")
        engine.op2.set(MinusTwoInputs())
        engine.op2.setup(in_name=["in2", "middle"], out_name="out")

        # an input is missing
        with self.assertRaises(CelloError):
            res = engine.play(10)
    
        res = engine.play(in1=10, in2=2)
        self.assertEquals(len(res), 4)
        self.assertEquals(res["middle"], 50)
        self.assertEquals(res["out"], -48)

