Get started
===========

Simple reliure pipeline
--------------------

Here is a very simple pipeline of two components:

>>> from reliure import Composable
>>> plus_two = Composable(lambda x: x+2)
>>> times_three = Composable(lambda x: x*3)
>>> pipeline = plus_two | times_three
>>> # one can then run it :
>>> pipeline(3)
15
>>> pipeline(10)
36


Build a more complex component
--------------------------

A reliure compenent is basicely function with spectial wrapping arround to make
it "pipeline-able". In other word it is a *callable* object that inherit from
:class:`reliure.Composable`.

You can build it using :class:`reliure.Composable` as a decorator.

>>> @Composable
... def my_processing(value):
...     return value**2
...
>>> my_processing(2)
4
>>> my_processing.name      # this has been added by Composable
'my_processing'

Or you can build a class that inherit from :class:`reliure.Composable`:

>>> class MyProcessing(Composable):
...     def __init__(self, pow):
...         super(MyProcessing, self).__init__()
...         self.pow = pow
... 
...     def __call__(self, intdata):
...         return intdata**self.pow
... 
>>> my_processing = MyProcessing(4)
>>> my_processing.name
'MyProcessing'
>>> my_processing(2)
16


Make a Optionable component
------------------------

An other key feature of reliure is to have :class:`reliure.Optionable` components:

    >>> from reliure import Optionable
    >>> from reliure.types import Numeric
    >>> class ProcessWithOption(Optionable):
    ...     def __init__(self):
    ...         super(ProcessWithOption, self).__init__()
    ...         self.add_option("pow", Numeric(default=2, help="power to apply", min=0))
    ... 
    ...     @Optionable.check
    ...     def __call__(self, intdata, pow=None):
    ...         return intdata**pow
    ... 
    >>> my_processing = ProcessWithOption()
    >>> my_processing.name
    'ProcessWithOption'
    >>> my_processing(2)
    4
    >>> my_processing(2, pow=4)
    16
    >>> my_processing(2, pow=-2)
    Traceback (most recent call last):
    ValidationError: [u'Ensure this value ("-2") is greater than or equal to 0.']
    >>> 2
    2

Fin de la doc


