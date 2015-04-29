#-*- coding:utf-8 -*-
""" :mod:`reliure.utils`
======================

.. toctree::

    reliure.utils.log
    reliure.utils.i18n
    reliure.utils.cli

"""

import re
import logging
import json

def parse_bool(value):
    """ Convert a string to a boolean
    
    >>> parse_bool(None)
    False
    >>> parse_bool("true")
    True
    >>> parse_bool("TRUE")
    True
    >>> parse_bool("yes")
    True
    >>> parse_bool("1")
    True
    >>> parse_bool("false")
    False
    >>> parse_bool("sqdf")
    False
    >>> parse_bool(False)
    False
    >>> parse_bool(True)
    True
    """
    if value is None:
        return False
    if value is True or value is False:
        return value
    boolean = str(value).strip().lower()
    return boolean in ['true', 'yes', 'on', '1']


JSON_CLEAN_LAST_COMMA = re.compile(",([\s]*\})")
def _json_text_clean(json_text):
    return JSON_CLEAN_LAST_COMMA.sub(r"\1", json_text).strip()


def deprecated(new_fct_name, logger=None):
    """ Decorator to notify that a fct is deprecated
    """
    if logger is None:
        logger = logging.getLogger("kodex")
    nfct_name = new_fct_name
    def aux_deprecated(func):
        """This is a decorator which can be used to mark functions
        as deprecated. It will result in a warning being emmitted
        when the function is used."""
        def newFunc(*args, **kwargs):
            msg = "DeprecationWarning: use '%s' instead of '%s'." % (new_fct_name, func.__name__)
            logger.warning(msg)
            warnings.warn(msg, category=DeprecationWarning)
            return func(*args, **kwargs)
        newFunc.__name__ = func.__name__
        newFunc.__doc__ = func.__doc__
        newFunc.__dict__.update(func.__dict__)
        return newFunc
    return aux_deprecated


def engine_schema(engine, out_names=None, filename=None, format="pdf"):
    """ Build a graphviz schema of a reliure :class:`.Engine`.
    
    It depends on `graphviz <https://pypi.python.org/pypi/graphviz>`_.

    :param engine: reliure engine to graph
    :type engine: :class:`.Engine`
    :param out_names: list of block output to consider as engine output (all by default)
    :param filename: output filename, create the file if given
    :param formal: output file formal (pdf, svg, png, ...)

    >>> from reliure.engine import Engine
    >>> egn = Engine("preproc", "proc1", "proc2")
    >>> egn.preproc.setup(in_name="input", out_name="data")
    >>> egn.proc1.setup(in_name="data", out_name="gold_data")
    >>> egn.proc2.setup(in_name="input", out_name="silver_data")
    >>> # you can create
    >>> schema = engine_schema(egn, filename='docs/img/engine_schema', format='png')

    it create the following image :

    .. image:: /../_static/engine_schema.png

    You can specify which block output will be consider as engine output:

    >>> schema = engine_schema(egn, ["gold_data", "silver_data"], filename='docs/img/engine_schema_simple', format='png')

    .. image:: /../_static/engine_schema_simple.png

    Note that it is also possible to draw a pdf;

    >>> schema = engine_schema(egn, ["gold_data", "silver_data"], filename='docs/img/engine_schema_simple', format='pdf')
    """
    import graphviz as pgv
    #engine.validate()
    dg = pgv.Digraph(format=format)
    input_node_name = "in"
    output_node_name = "out"
    dg.node(input_node_name, label=input_node_name, shape="ellipse")
    block_source = {} # witch block is the source for witch data
    for e_in_name in engine.in_name:
        block_source[e_in_name] = input_node_name
    # creation des sommets
    for block in engine:
        dg.node(block.name, label=' %s ' % block.name, shape="box")
    # creation des liens
    for block in engine:
        for in_name in block.in_name:
            dg.edge(block_source[in_name], block.name,
                label=" %s " % in_name,
                #fontsize=10,
            )
        block_source[block.out_name] = block.name
    
    if out_names is None:
        out_names = set([block.out_name for block in engine])
    
    if len(out_names):
        dg.node(output_node_name, label=' %s ' % output_node_name, shape="ellipse")
        for out_name in out_names:
            if out_name not in block_source:
                raise ValueError("'%s' is not a generated data" % out_name)
            dg.edge(block_source[out_name], output_node_name,
                label=" %s " % out_name,
                #fontsize=10,
            )
    if filename:
        dg.render(filename)
    return dg

