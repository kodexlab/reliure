.. _reliure-offline:

.. add some hidden import code
.. doctest::
    :hide:

    >>> from pprint import pprint
    >>> import json

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
###########################

TODO

see :mod:`.reliure.utils.cli`
