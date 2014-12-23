Get started
===========

simple reliure pipeline
-----------------------

Here is a very simple pipeline of two component ::

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
------------------------------


A reliure compenent is basicely function with spectial wrapping arround to make
it "pipeline-able". In other word it is a *callable* object that inherit from
:class:`.Composable`.

You can build it using :class:`.Composable` as a decorator.

    >>> @Composable
    ... def my_processing(intdata):
    ...     return intdata**2
    ...
    >>> my_processing(2)
    4
    >>> my_processing.name      # this has been added by Composable
    'my_processing'

Or you can build a class that inherit from :class:`.Composable`:

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

