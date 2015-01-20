.. _reliure-web:

.. add some hidden import code
.. doctest::
    :hide:

    >>> from pprint import pprint
    >>> import json

.. Utils

.. |br| raw:: html

   <br />

******************
Build a Json API
******************

Reliure permits to build json api for simple processing function (or :class:`Optionable`)
as well as for more complex :class:`.Engine`. The idea of the reliure API
mechanism is : you manage data processing logic, reliure manages the "glue" job.

Reliure web API are based on `Flask <http://flask.pocoo.org/>`_.
A reliure API (:class:`ReliureAPI`) is a Flask :class:`.Blueprint` where you plug view of your 
processing modules.

Let's see how it works on some simple examples !


.. contents:: `Table of contents`
   :depth: 5
   :local:

Component or simple function
#############################

Expose a simple function
==========================

Let's imagine that we have the following hyper-complex data procesing method:

>>> def count_a_and_b(chaine):
...     return chaine.count("a") + chaine.count("b")

and you want it to be accessible on an HTTP/json supercool-powered API...
In ohter word we just want that a GET on ``http://myapi.me.com/api/count_ab/totocotata``
returns ``2`` and eventualy some other metadata (processing time for instance).

Here is how we can do that with reliure.

First you need to build a "view" (a :class:`.ComponentView`) on this function:

>>> from reliure.web import ComponentView
>>> view = ComponentView(count_a_and_b)

Then you have to define the type of the input (the type will manage parsing
from string/json):

>>> from reliure.types import Text
>>> view.add_input("in", Text())
>>> # Note that, by default, the output will be named with the function name

You can also specify a short url patern to reach your function,
this is done with flask route paterns syntax.
Here we will simply indicate that the url (note that there will be url prefix)
should match our uniq input:

>>> view.play_route("<in>")

Then you can create a :class:`.ReliureAPI` object and register this view on it:

>>> from reliure.web import ReliureAPI
>>> api = ReliureAPI("api")
>>> api.register_view(view, url_prefix="count_ab")

This ``api`` object can be plug to a flask app (it is a Flask :class:`.Blueprint`):

>>> from flask import Flask
>>> app = Flask("my_app")
>>> app.register_blueprint(api, url_prefix="/api")


.. doctest::
    :hide:

    >>> app.config['TESTING'] = True    # this is just for testing purpose
    >>> client = app.test_client()              # get a test client for our app

To illustrate API call, let's use Flask testing mechanism:

>>> resp = client.get("/api/count_ab/abcdea")    # call our API
>>> results = json.loads(resp.data)
>>> pprint(results["results"])
{u'count_a_and_b': 3}
>>> 
>>> resp = client.get("/api/count_ab/abcdea__bb_aaa")
>>> results = json.loads(resp.data)
>>> pprint(results["results"])
{u'count_a_and_b': 8}

Note that meta information is also available:

>>> pprint(results["meta"])         #doctest: +SKIP
{u'details': [{u'errors': [],
               u'name': u'count_a_and_b',
               u'time': 3.314018249511719e-05,
               u'warnings': []}],
 u'errors': [],
 u'name': u'count_a_and_b:[count_a_and_b]',
 u'time': 3.314018249511719e-05,
 u'warnings': []}


Managing options and multiple inputs
=====================================

Let's mouv on a more complex exemple...

First, write your processing component
--------------------------------------

One can imagine the following component that merge two string with two
possible methods (choice is made with an option):

>>> from reliure import Optionable
>>> from reliure.types import Text
>>>
>>> class StringMerge(Optionable):
...     """ Stupid component that merge to string together
...     """
...     def __init__(self):
...         super(StringMerge, self).__init__()
...         self.add_option("method", Text(
...             choices=[u"concat", u"altern"],
...             default=u"concat",
...             help="How to merge the inputs"
...         ))
... 
...     @Optionable.check
...     def __call__(self, left, right, method=None):
...         if method == u"altern":
...             merge = "".join("".join(each) for each in zip(left, right))
...         else:
...             merge = left + right
...         return merge

One can use this directly in python:

>>> merge_component = StringMerge()
>>> merge_component("aaa", "bbb")
'aaabbb'
>>> merge_component("aaa", "bbb", method=u"altern")
'ababab'


Then create a view on it, and register it on your API
-----------------------------------------------------

If you want to expose this component on a HTTP API,
as for our first exemple,
you need to build a "view" (a :class:`.ComponentView`) on it:

>>> view = ComponentView(merge_component)
>>> # you need to define the type of the input
>>> from reliure.types import Text
>>> view.add_input("in_lft", Text())
>>> view.add_input("in_rgh", Text(default=u"ddd"))
>>> # ^ Note that it is possible to give default value for inputs
>>> view.add_output("merge")
>>> # we specify two short urls to reach the function:
>>> view.play_route("<in_lft>/<in_rgh>", "<in_lft>")

.. warning:: Note that for a :class:`ComponentView` the *order* of the inputs
    matters to match with component (or function) arguments.
    It is not the name of that permits the match.


.. warning:: when you define default value for inputs, ``None`` can not be a default value.

.. doctest::
    :hide:

    >>> api = ReliureAPI("api")

Then we can register this new view to a reliure API object:

>>> api.register_view(view, url_prefix="merge")

.. doctest::
    :hide:

    >>> # create a testing app (and client)
    >>> app = Flask("my_app")
    >>> app.register_blueprint(api, url_prefix="/api")
    >>> app.config['TESTING'] = True            # this is just for testing purpose
    >>> client = app.test_client()              # get a test client for our app


Finaly, just use !
-------------------

And then we can use it:

>>> resp = client.get("/api/merge/aaa/bbb")
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'aaabbb'}


As we have specify a route that require only one argument, and a default value
for this second input (``in_rgh``), it is also possible to do:

>>> resp = client.get("/api/merge/aaa")
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'aaaddd'}

It is also possible to call the API with options:

>>> resp = client.get("/api/merge/aaa/bbb?method=altern")
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'ababab'}

Alternatively you can use a POST to send inputs.
There is two posibility to provide inputs and options.
First by using direct form encoding:

>>> resp = client.post("/api/merge", data={"in_lft":"ee", "in_rgh":"hhhh"})
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'eehhhh'}

And with options in the url:

>>> resp = client.post("/api/merge?method=altern", data={"in_lft":"ee", "in_rgh":"hhhh"})
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'eheh'}

The second option is to use a json payload:

>>> data = {
...     "in_lft":"eeee",
...     "in_rgh":"gg",
...     "options": {
...         "name": "StringMerge",
...         "options": {
...             "method": "altern",
...         }
...     }
... }
>>> json_data = json.dumps(data)
>>> resp = client.post("/api/merge", data=json_data, content_type='application/json')
>>> # note that it is important to specify content_type to 'application/json'
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'egeg'}


Note that a GET call on the root ``/api/merge`` returns a json that specify
the API. With this, it is possible do list all the options of the component:

>>> resp = client.get("/api/merge")
>>> results = json.loads(resp.data)
>>> pprint(results)
{u'args': [u'in_lft', u'in_rgh'],
 u'components': [{u'default': True,
                  u'name': u'StringMerge',
                  u'options': [{u'name': u'method',
                                u'otype': {u'choices': [u'concat',
                                                        u'altern'],
                                           u'default': u'concat',
                                           u'help': u'How to merge the inputs',
                                           u'multi': False,
                                           u'type': u'Text',
                                           u'uniq': False,
                                           u'vtype': u'unicode'},
                                u'type': u'value',
                                u'value': u'concat'}]}],
 u'multiple': False,
 u'name': u'StringMerge',
 u'required': True,
 u'returns': [u'merge']}



Complex processing engine
################################

Define your engine
====================

Here is a simple reliure engine that we will expose as an HTTP API.

>>> from reliure.engine import Engine
>>> engine = Engine("vowel", "consonant", "concat")
>>> engine.vowel.setup(in_name="text")
>>> engine.consonant.setup(in_name="text")
>>> engine.concat.setup(in_name=["vowel", "consonant"], out_name="merge")
>>>
>>> from reliure import Composable
>>> vowels = u"aiueoéèàùêôûîï"
>>> @Composable
... def extract_vowel(text):
...     return "".join(char for char in text if char in vowels)
>>> engine.vowel.set(extract_vowel)
>>>
>>> @Composable
... def extract_consonant(text):
...     return "".join(char for char in text if char not in vowels)
>>> engine.consonant.set(extract_consonant)
>>>
>>> # for the merge we re-use the component defined in previous section:
>>> engine.concat.set(StringMerge())

The Figure :ref:`engine-schema` draw the processing schema of this small engine.

.. _engine-schema:

.. figure:: /_static/engine_schema_vowel_consonent.png
    :align: center
    :height: 200px
    :alt: Engine schema
    :figclass: align-center

    Engine schema.

    Exemple of engine that we will expose as an API. |br|
    (See :func:`.engine_schema` to see how to generate such schema from an engine)

    .. Generation du png :

    .. doctest::
        :hide:

        >>> from reliure.utils import engine_schema
        >>> schema = engine_schema(engine, ["merge"])
        >>> schema.draw('docs/img/engine_schema_vowel_consonent.png', prog='dot')


Create a view and register it on your api
============================================

As for a simple component we need to create a view over our engine :

>>> from reliure.web import EngineView
>>> view = EngineView(engine)

And then to define the input and output types:

>>> view.add_input("text", Text())
>>> view.add_output("merge", Text())

We can also specify a short url patern to run the engine:

>>> view.play_route("<text>")

Then you can create a :class:`.ReliureAPI` object and register this view on it:

.. doctest::
    :hide:

    >>> api = ReliureAPI("api")

Then we can register this new view to a reliure API object:

>>> api.register_view(view, url_prefix="process")

.. doctest::
    :hide:

    >>> # create a testing app (and client)
    >>> app = Flask("my_app")
    >>> app.register_blueprint(api, url_prefix="/api")
    >>> app.config['TESTING'] = True            # this is just for testing purpose
    >>> client = app.test_client()              # get a test client for our app


Use it !
===========

>>> resp = client.get("/api/process/abcdea")
>>> results = json.loads(resp.data)
>>> pprint(results["results"])
{u'merge': u'aeabcd'}
>>> 
>>> resp = client.get("/api/process/abcdea__bb_aaa")
>>> results = json.loads(resp.data)
>>> pprint(results["results"])
{u'merge': u'aeaaaabcd__bb_'}

Note that meta information is also available:

>>> pprint(results["meta"])     # doctest: +SKIP
    {u'details': [{u'details': [{u'errors': [],
                                 u'name': u'extract_vowel',
                                 u'time': 3.695487976074219e-05,
                                 u'warnings': []}],
                   u'errors': [],
                   u'name': u'vowel:[extract_vowel]',
                   u'time': 3.695487976074219e-05,
                   u'warnings': []},
                  {u'details': [{u'errors': [],
                                 u'name': u'extract_consonant',
                                 u'time': 3.0040740966796875e-05,
                                 u'warnings': []}],
                   u'errors': [],
                   u'name': u'consonant:[extract_consonant]',
                   u'time': 3.0040740966796875e-05,
                   u'warnings': []},
                  {u'details': [{u'errors': [],
                                 u'name': u'StringMerge',
                                 u'time': 5.507469177246094e-05,
                                 u'warnings': []}],
                   u'errors': [],
                   u'name': u'concat:[StringMerge]',
                   u'time': 5.507469177246094e-05,
                   u'warnings': []}],
     u'errors': [],
     u'name': u'engine:[vowel:[extract_vowel], consonant:[extract_consonant], concat:[StringMerge]]',
     u'time': 0.0001220703125,
     u'warnings': []}

