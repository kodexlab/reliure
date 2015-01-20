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

>>> from reliure.web import ComponentView
>>> view = ComponentView(count_a_and_b)
>>> # you need to define the type of the input
>>> from reliure.types import Text
>>> view.add_input("in", Text())
>>> # Note that the output is named with your function name by default
>>> 
>>> # you can also specify a short url to reach your function
>>> view.play_route("<in>")

Then you can register this view on a reliure API object:

>>> from reliure.web import ReliureAPI
>>> api = ReliureAPI("api")
>>> api.register_view(view, url_prefix="cab")

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



Managing multiple inputs, more complex component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One can imagine the following component that merge two sting with two different
methods:

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
...             help="Wheter to merge the inputs"
...         ))
... 
...     @Optionable.check
...     def __call__(self, left, right, method=None):
...         if method == u"altern":
...             merge = "".join("".join(each) for each in zip(left, right))
...         else:
...             merge = left+right
...         return merge

You need to build a "view" (a :class:`.ComponentView`) on this function:

>>> from reliure.web import ComponentView
>>> merge_component = StringMerge()
>>> view = ComponentView(merge_component)
>>> # you need to define the type of the input
>>> from reliure.types import Text
>>> view.add_input("in_lft", Text())
>>> view.add_input("in_rgt", Text())
>>> # Note that here it is not the name of the inputs that matter *BUT* the order
>>> view.add_output("merge")
>>> 
>>> # you can also specify a short url to reach your function
>>> view.play_route("<in_lft>/<in_rgt>")

Then we can register this new view to a reliure API object:

>>> api = ReliureAPI("api")
>>> api.register_view(view, url_prefix="merge")
>>> # create a testing app (and client)
>>> app = Flask("my_app")
>>> app.register_blueprint(api, url_prefix="/api")
>>> app.config['TESTING'] = True            # this is just for testing purpose
>>> client = app.test_client()              # get a test client for our app

And then we can do :

>>> resp = client.get("/api/merge/aaa/bbb")
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'aaabbb'}

It is also possible to call the API with options:

>>> resp = client.get("/api/merge/aaa/bbb?method=altern")    # call our API
>>> results = json.loads(resp.data)
>>> results["results"]
{u'merge': u'ababab'}

On can also list the options of this component:

>>> resp = client.get("/api/merge")
>>> results = json.loads(resp.data)
>>> from pprint import pprint
>>> pprint(results)
{u'args': [u'in_lft', u'in_rgt'],
 u'components': [{u'default': True,
                  u'name': u'StringMerge',
                  u'options': [{u'name': u'method',
                                u'otype': {u'choices': [u'concat',
                                                        u'altern'],
                                           u'default': u'concat',
                                           u'help': u'Wheter to merge the inputs',
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



Plug a complex processing engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

{{TODO}}


