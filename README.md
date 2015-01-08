Reliure is a minimal and basic framework to manage pipeline of data processing
components in Python.


Install
======

    $ pip install reliure

License
=======

Reliure source code is available under the [LGPL Version 3](http://www.gnu.org/licenses/lgpl.txt) license, unless otherwise indicated.

Doc
===

How to generate the doc ?

$ make doc

Requires
=======

* py.test for testing
* sphinx for documenation

Contribute
==========

    $ # Clone it
    $ cd reliure
    $ virtualenv ENV
    $ source ENV/bin/activate
    $ pip install -r requirements.txt
    $ pip install -e ./

To run tests:

    $ pip install -I pytest
    $ make testall

To build the doc:

    $ pip install -I sphinx
    $ pip install -I sphinx_rtd_theme
    $ make doc

then open: docs/_build/html/index.html


