.. _reliure-offline:

.. add some hidden import code
.. doctest::
    :hide:

    >>> from pprint import pprint
    >>> import json
    >>> from reliure import Optionable

******************
Offline processing
******************

Reliure provides some helpers to run offline bash processing.


.. contents:: `Table of contents`
   :depth: 5
   :local:


Run a component, or pipeline of components
#############################################

To illustrate how you can easily run a pipeline of components with reliure, 
let's consider that we have a sequence of "document" we want to process:

>>> documents = ["doc1", "doc2", "doc3", "doc4"]

For that we have this two components, that we pipe:

>>> from reliure.pipeline import Composable
>>> @Composable
... def doc_analyse(docs):
...     for doc in docs:
...         yield {
...             "title": doc,
...             "id": int(doc[3:]),
...             "url": "http://lost.com/%s" % doc,
...         }
>>>
>>> @Composable
... def print_ulrs(docs):
...     for doc in docs:
...         print(doc["url"])
...         yield doc
>>>
>>> pipeline = doc_analyse | print_ulrs

To run this pipeline on our documents, you just have to do:

>>> from reliure.offline import run
>>> res = run(pipeline, documents)
http://lost.com/doc1
http://lost.com/doc2
http://lost.com/doc3
http://lost.com/doc4
>>> pprint(res)
[{'id': 1, 'title': 'doc1', 'url': 'http://lost.com/doc1'},
 {'id': 2, 'title': 'doc2', 'url': 'http://lost.com/doc2'},
 {'id': 3, 'title': 'doc3', 'url': 'http://lost.com/doc3'},
 {'id': 4, 'title': 'doc4', 'url': 'http://lost.com/doc4'}]

The exact same pipeline can now be run in // by using :func:`run_parallel`
instead of :func:`run`:

>>> from reliure.offline import run_parallel
>>> res = run_parallel(pipeline, documents, ncpu=2, chunksize=5)

Command line interface
#########################

:mod:`.reliure.utils.cli` provides some helper to create or populate
`argument parser <https://docs.python.org/3/library/argparse.html>`_ from Optionable.
Let's look at a simple exemple.

First you have an Optionable component with an option:

>>> class PowerBy(Optionable):
...    def __init__(self):
...        super(PowerBy, self).__init__("testOptionableName")
...        self.add_option("alpha", Numeric(default=4, min=1, max=20,
...                        help='power exponent'))
...
...    @Optionable.check
...    def __call__(self, value, alpha=None):
...        return value**alpha
>>>

Note that it could aslo be a pipeline of components.

Next you want to build a script with a `__main__` and you want to map your
component options to script option using `argparse`. Here is how to do
(file `reliure_cli.py`:

.. literalinclude:: examples/reliure_cli.py

With that you will have a nice doc generated:

.. code-block:: shell

    $ python reliure_cli.py -h
    usage: reliure_cli.py [-h] [--power_alpha POWER_ALPHA] INPUT

    positional arguments:
      INPUT                 the number to process !

    optional arguments:
      -h, --help            show this help message and exit
      --power_alpha POWER_ALPHA
                            power exponent

    $ python reliure_cli.py --power_alpha 3 3
    27

