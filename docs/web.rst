.. _reliure-web:

Build a Json API
================

Reliure permits to build JSON api from simple function or more complex :class:`.Engine`.


Expose a simple function
~~~~~~~~~~~~~~~~~~~~~~~~

>>> def count_a_and_b(chaine):
...     return chaine.count("a") + chaine.count("b")
>>> 
>>> from reliure.utils.web import ComponentView
>>> from reliure.types import Text
>>> view = ComponentView(count_a_and_b)
>>> view.add_input("in", Text())
>>> view.get("<in>")
>>>
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

>>> import json
>>> client = app.test_client()              # get a test client for our app
>>> resp = client.get("/api/cab/abcdea")    # call our API
>>> results = json.loads(resp.data)
>>> results["results"]
{u'count_a_and_b': 3}

