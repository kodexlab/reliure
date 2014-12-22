Get started: setup a simple Reliure pipeline
==========================================

Here is a very simple pipeline of two component ::

    >>> from reliure.pipeline import Composable
    >>> plus_two = Composable(lambda x: x+2)
    >>> times_three = Composable(lambda x: x*3)
    >>> pipeline = plus_two | times_three
    >>> # one can then run it :
    >>> pipeline(3)
    15
    >>> pipeline(10)
    36


The exemple
-----------

All TODO


.. warning::

    Never, ever, use this code!
