#-*- coding:utf-8 -*-
""" :mod:`reliure.utils`
======================

.. toctree::

    reliure.utils.log
    reliure.utils.i18n
    reliure.utils.cli
    reliure.utils.web

"""

import re
import urllib2
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


def urllib2_json_urlopen(request_url, request_data=None, logger=None):
    """ Make a request with urllib2 and retrive a JSON (in unicode)
    """
    #TODO use requests
    if isinstance(request_url, unicode):
        request_url = request_url.encode('utf8')
    
    if logger is not None:
        logger.debug("urllib2: open url = %s" % request_url)
        logger.debug("urllib2: with params = %s" % request_data)
    
    response = urllib2.urlopen(request_url, request_data)
    json_text = response.read()
    json_text = _json_text_clean(json_text)
    if isinstance(json_text, str):
        json_text = json_text.decode('utf8')
    # data are provided in json
    try:
        results = json.loads(json_text)
    except ValueError:
        logger.error("Fail to parse the json: %s" % json_text)
        raise
    response.close()
    return results

def urllib2_setup_proxy(proxy=None):
    """ Setup a proxy for urllib2
    """
    # urllib2 tries to use the proxy to find the localhost
    # Proxy support may not work at irit if no empty is set for the request
    if proxy:
        proxy_support = urllib2.ProxyHandler({'http' : proxy})
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)


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

def engine_schema(engine, out_names=None):
    """ Build a graphviz schema of a reliure :class:`.Engine`.
    
    It depends on `pygraphviz <http://pygraphviz.github.io/>`_.

    :param engine: The reliure engine to graph
    :type engine: :class:`.Engine`
    :param out_names: list of block output to consider as engine output (all by default)

    >>> from reliure.engine import Engine
    >>> egn = Engine("preproc", "proc1", "proc2")
    >>> egn.preproc.setup(in_name="input", out_name="data")
    >>> egn.proc1.setup(in_name="data", out_name="gold_data")
    >>> egn.proc2.setup(in_name="input", out_name="silver_data")
    >>> # you can create 
    >>> schema = engine_schema(egn)
    >>> schema.draw('docs/img/engine_schema.png', prog='dot')

    it create the following image :

    .. image:: /../_static/engine_schema.png

    You can spécify which block output will be consider as engine output:

    >>> schema = engine_schema(egn, ["gold_data", "silver_data"])
    >>> schema.draw('docs/img/engine_schema_simple.png', prog='dot')

    .. image:: /../_static/engine_schema_simple.png

    Note that it is also possible to draw a pdf;

    >>> schema.draw('docs/img/engine_schema.pdf', prog='dot')
    """
    import pygraphviz as pgv
    #engine.validate()
    dg = pgv.AGraph(strict=False, directed=True)
    input_node_name = "in"
    output_node_name = "out"
    dg.add_node(input_node_name, label=input_node_name, shape="ellipse")
    block_source = {} # witch block is the source for witch data
    for e_in_name in engine.in_name:
        block_source[e_in_name] = input_node_name
    # creation des sommets
    for block in engine:
        dg.add_node(block.name, label=' %s ' % block.name, shape="box")
    # creation des liens
    for block in engine:
        for in_name in block.in_name:
            dg.add_edge(block_source[in_name], block.name,
                label=" %s " % in_name,
                fontsize=10,
            )
        block_source[block.out_name] = block.name
    
    if out_names is None:
        out_names = set([block.out_name for block in engine])
    
    if len(out_names):
        dg.add_node(output_node_name, label=' %s ' % output_node_name, shape="ellipse")
        for out_name in out_names:
            if out_name not in block_source:
                raise ValueError("'%s' is not a generated data" % out_name)
            dg.add_edge(block_source[out_name], output_node_name,
                label=" %s " % out_name,
                fontsize=10,
            )
    return dg

