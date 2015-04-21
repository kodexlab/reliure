Reliure is a minimal and basic framework to manage pipeline of data processing
components in Python.


Install
======

    $ pip install reliure

License
=======

Reliure source code is available under the [LGPL Version 3](http://www.gnu.org/licenses/lgpl.txt) license, unless otherwise indicated.


Summary of requirements
======================

* py.test for testing
* sphinx for documenation

See requirements.txt or a full list of python packages dep

Contribute
==========

    $ # Clone it
    $ cd reliure
    $ virtualenv ENV
    $ source ENV/bin/activate
    $ pip install -r requirements.txt

To run tests:

    $ pip install -I pytest
    $ make testall

To build the doc:

    $ pip install -I sphinx
    $ pip install -I sphinx_rtd_theme
    $ make doc

then open: docs/_build/html/index.html


**Warning**: You need to have `reliure` accesible in the python path to run tests (and to build doc).
For that you can install `reliure` as a link in local virtualenv:

    $ pip install -e .

(Note: this is indicadet in pytest good practice https://pytest.org/latest/goodpractises.html )


If you dev, in the same time, an other package than need your last reliure version, you can use : 

    $ pip install -e th_good_path/reliure                 # link reliure in local python packages