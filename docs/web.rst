.. _reliure-web:

Build a Json API
================

Reliure permits to build json api from simple function or more complex :class:`.Engine`.


Expose a simple function
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to expose on a http/json api a simple processing function:

>>> def count_a_and_b(chaine):
...     return chaine.count("a") + chaine.count("b")

You need to build a "view" (a :class:`.ComponentView`) on this function:

>>> from reliure.utils.web import ComponentView
>>> view = ComponentView(count_a_and_b)
>>> # you need to define the type of the input
>>> from reliure.types import Text
>>> view.add_input("in", Text())
>>> # Note that the output is named with your function name by default
>>> 
>>> # you can also specify a short url to reach your function
>>> view.get("<in>")

Then you can register this view on a reliure API object:

>>> from reliure.utils.web import ReliureJsonAPI
>>> api = ReliureJsonAPI("api")
>>> api.plug(view, url_prefix="cab")

This api can be plug to a flask app:

>>> from flask import Flask
>>> app = Flask("my_app")
>>> app.config['TESTING'] = True    # this is just for testing purpose
>>>
>>> # you can register your api this way:
>>> app.register_blueprint(api, url_prefix="/api")

To illustrate API call, let's use flask testing mechanism:

>>> import json
>>> client = app.test_client()              # get a test client for our app
>>> 
>>> resp = client.get("/api/cab/abcdea")    # call our API
>>> results = json.loads(resp.data)
>>> results["results"]
{u'count_a_and_b': 3}
>>> 
>>> resp = client.get("/api/cab/abcdea__bb_aaa")    # call our API
>>> results = json.loads(resp.data)
>>> results["results"]
{u'count_a_and_b': 8}

