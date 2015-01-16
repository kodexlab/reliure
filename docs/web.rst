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
>>> view.get("/<in>")
>>>
>>> from reliure.utils.web import ReliureJsonAPI
>>> api = ReliureJsonAPI("api")
>>> api.plug(view, url_prefix="cab")
