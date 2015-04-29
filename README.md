# reliure: minimal framework for data processing

`reliure` is a minimal and basic framework to manage pipeline of data processing
components in Python.


## Install

    $ pip install reliure

## License

`reliure` source code is available under the [LGPL Version 3](http://www.gnu.org/licenses/lgpl.txt) license, unless otherwise indicated.


## Summary of requirements

`reliure` works with python 2 and python 3. Note however that doctest (in source
files and in documentation .rst) only works with python 3.

`reliure` depends only on:
* flask, for web API mechanism
* requests, for API clients
* graphviz, for engine schema generation

All this deps may be installed with:

    $ pip install -r requirements.txt

To develop reliure you will also need:
* py.test for testing
* sphinx for documenation

Dev dependances may be installed with:

    $ pip install -r requirements.dev.txt


## Contribute

    $ # Clone it
    $ cd reliure
    $ virtualenv ENV
    $ source ENV/bin/activate
    $ pip install -r requirements.txt
    $ pip install -r requirements.dev.txt

To run tests:

    $ make testall

To build the doc:

    $ make doc

then open: docs/_build/html/index.html


**Warning**: You need to have `reliure` accesible in the python path to run tests (and to build doc).
For that you can install `reliure` as a link in local virtualenv:

    $ pip install -e .

(Note: this is indicadet in pytest good practice https://pytest.org/latest/goodpractises.html )


If you dev, in the same time, an other package than need your last reliure version, you can use : 

    $ pip install -e th_good_path/reliure                 # link reliure in local python packages