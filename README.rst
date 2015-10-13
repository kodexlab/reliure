Reliure: minimal framework for data processing
===============================================

``reliure`` is a minimal and basic framework to manage pipeline of data
processing components in Python.

Documentation
=============

In case your are not reading it yet, full documentation is available on
*ReadTheDoc*: http://reliure.readthedocs.org

Install
=======

Should be simple as a pip command::

    $ pip install reliure

License
=======

``reliure`` source code is available under the `LGPL Version 3 <http://www.gnu.org/licenses/lgpl.txt>`_ license, unless otherwise indicated.


Requirements
============

``reliure`` works with both Python 2 and Python 3. it depends on:

* `flask <http://flask.pocoo.org/>`_ for web API mechanism,
* `requests <http://docs.python-requests.org/>`_ for API clients,
* `graphviz <http://graphviz.readthedocs.org/en/latest/>`_ for engine schema generation,

All this deps may be installed with::

    $ pip install -r requirements.txt

To develop reliure you will also need:

* `py.test <http://pytest.org/>`_ for testing
* `sphinx <http://sphinx-doc.org/>`_ for documenation

Dev dependances may be installed with::

    $ pip install -r requirements.dev.txt


Contribute
==========

The following should create a pretty good development environment::

    $ git clone https://github.com/kodexlab/reliure.git
    $ cd reliure
    $ virtualenv ENV
    $ source ENV/bin/activate
    $ pip install -r requirements.txt
    $ pip install -r requirements.dev.txt

To run tests::

    $ make testall

To build the doc::

    $ make doc

then open: ``docs/_build/html/index.html``


.. Warning:: You need to have `reliure` accesible in the python path to run
  tests (and to build doc). For that you can install `reliure` as a link in local virtualenv::

    $ pip install -e .

  (Note: this is indicadet in `pytest good practice <https://pytest.org/latest/goodpractises.html>`_ )


If you dev, in the same time, an other package than need your last reliure version, you can use::

    $ pip install -e the_good_path/reliure  # link reliure in local python packages


