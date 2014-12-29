.. _reliure-engine:

Reliure Engine
==============

simple exemple
~~~~~~~~~~~~~~

TODO !

wtf exemple
~~~~~~~~~~~

Here is a simple exemple of :class:`.Engine` usage.
First you need to setup your engine:

>>> from reliure.engine import Engine
>>> egn = Engine()
>>> egn.requires('foo', 'bar', 'boo')

one can make imaginary components:

>>> from reliure.pipeline import Pipeline, Optionable, Composable
>>> from reliure.types import Numeric
>>> class One(Optionable):
...     def __init__(self):
...         super(One, self).__init__(name="one")
...         self.add_option("val", Numeric(default=1))
... 
...     @Optionable.check
...     def __call__(self, input, val=None):
...         return input + val
... 
>>> one = One()
>>> two = Composable(name="two", func=lambda x: x*2)
>>> three = Composable(lambda x: x - 2) | Composable(lambda x: x/2.)
>>> three.name = "three"

one can configure a block with this three components:

>>> foo_comps = [one, two, three]
>>> foo_options = {'defaults': 'two'}
>>> egn.set('foo', *foo_comps, **foo_options)

or

>>> egn['bar'].setup(multiple=True)
>>> egn['bar'].append(two, default=True)
>>> egn['bar'].append(three, default=True)

or

>>> egn["boo"].set(two, three)
>>> egn["boo"].setup(multiple=True)
>>> egn["boo"].defaults = [comp.name for comp in (two, three)]

One can have the list of all configurations:

>>> from pprint import pprint
>>> pprint(egn.as_dict())
{'args': ['input'],
 'blocks': [{'args': None,
             'components': [{'default': False,
                             'name': 'one',
                             'options': [{'name': 'val',
                                          'otype': {'choices': None,
                                                    'default': 1,
                                                    'help': '',
                                                    'max': None,
                                                    'min': None,
                                                    'multi': False,
                                                    'type': 'Numeric',
                                                    'uniq': False,
                                                    'vtype': 'int'},
                                          'type': 'value',
                                          'value': 1}]},
                            {'default': True,
                             'name': 'two',
                             'options': None},
                            {'default': False,
                             'name': 'three',
                             'options': []}],
             'multiple': False,
             'name': 'foo',
             'required': True,
             'returns': 'foo'},
            {'args': None,
             'components': [{'default': True,
                             'name': 'two',
                             'options': None},
                            {'default': True,
                             'name': 'three',
                             'options': []}],
             'multiple': True,
             'name': 'bar',
             'required': True,
             'returns': 'bar'},
            {'args': None,
             'components': [{'default': True,
                             'name': 'two',
                             'options': None},
                            {'default': True,
                             'name': 'three',
                             'options': []}],
             'multiple': True,
             'name': 'boo',
             'required': True,
             'returns': 'boo'}]}



And then you can configure and run it:

>>> request_options = {
...     'foo':[
...         {
...             'name': 'one',
...             'options': {
...                 'val': 2
...             }
...        },     # input + 2
...     ],
...     'bar':[
...         {'name': 'two'},
...     ],     # input * 2
...     'boo':[
...         {'name': 'two'},
...         {'name': 'three'},
...     ], # (input - 2) / 2.
... }
>>> egn.configure(request_options)
>>> # test before running:
>>> egn.validate()

One can then run only one block:

>>> egn['boo'].play(10)
4.0

or all blocks :

>>> res = egn.play(4)
>>> res['foo']      # 4 + 2
6
>>> res['bar']      # 6 * 2
12
>>> res['boo']      # (12 - 2) / 2.0
5.0

