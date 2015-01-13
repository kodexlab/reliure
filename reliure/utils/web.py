#-*- coding:utf-8 -*-
""" :mod:`reliure.utils.web`
============================

helpers to build HTTP/Json Api from reliure engines
"""

import sys
import json
import requests

from collections import OrderedDict

from flask import Flask
from flask import Blueprint
from flask import abort, request, jsonify

from reliure.types import GenericType, Text
from reliure.exceptions import ReliurePlayError
from reliure.engine import Engine

# for error code see http://fr.wikipedia.org/wiki/Liste_des_codes_HTTP#Erreur_du_client



def parse_request(request):
    """ Parse request for :func:`play`
    """
    data = {}
    options = {}
    
    ### get data
    if request.headers['Content-Type'].startswith('application/json'):
        # data in JSON
        data = request.json
        assert data is not None #FIXME: better error than assertError ?
        ### get the options
        if "options" in data:
            options = data["options"]
            del data["options"]
    else:
        # data in URL ?
        abort(415) # Unsupported Media Type
        # TODO: manage data in url
#            args = request.args
#            if args.get('_f') == 'semicolons':
#                pairs = args.get('q').split(',')
#                data['query'] = dict( tuple(x.split(':')) for x in pairs ) 

    #TODO: parse data according to self._inputs
    # note: all the inputs can realy be parsed only if the engine is setted
    return data, options

def run_engine(apiengine, inputs_data, options):
    """ Run the engine according to some inputs data and options
    """
    ### configure the engine
    try:
        apiengine.engine.configure(options)
    except ValueError as err:
        #TODO beter manage input error: indicate what's wrong
        abort(406)  # Not Acceptable

    ### Check inputs
    needed_inputs = apiengine.engine.needed_inputs()
    # check if all needed inputs are possible
    if not all([inname in apiengine._inputs for inname in needed_inputs]):
        #Note: this may be check staticly
        missing = [inname for inname in needed_inputs if inname not in apiengine._inputs]
        raise ValueError("With this configuration the inputs %s are needed but not declared." % missing)
    # check if all inputs are given
    if not all([inname in inputs_data for inname in needed_inputs]):
        # configuration error
        missing = [inname for inname in needed_inputs if inname not in inputs_data]
        raise ValueError("With this configuration the inputs %s are missing." % missing)
    #
    ### parse inputs (and validate)
    inputs = {}
    for inname in needed_inputs:
        input_val = apiengine._inputs[inname].parse(inputs_data[inname])
        apiengine._inputs[inname].validate(input_val)
        inputs[inname] = input_val
    #
    ### run the engine
    error = False # by default ok
    try:
        raw_res = apiengine.engine.play(**inputs)
    except ReliurePlayError as err:
        # this is the Reliure error that we can handle
        error = True
    finally:
        pass
    #
    ### prepare outputs
    outputs = {}
    results = {}
    if not error:
        # prepare the outputs
        for out_name, raw_out in raw_res.iteritems():
            if out_name not in apiengine._outputs:
                continue
            serializer = apiengine._outputs[out_name]
            # serialise output
            if serializer is not None:
                results[out_name] = serializer(raw_res[out_name])
            else:
                results[out_name] = raw_res[out_name]
    ### prepare the retourning json
    # add the results
    outputs["results"] = results
    ### serialise play metadata
    outputs['meta'] = apiengine.engine.meta.as_dict()
    #note: meta contains the error (if any)
    return outputs



class EngineView(object):
    def __init__(self, engine):
        self.engine = engine
        # default input
        self._inputs = OrderedDict()
        # default outputs
        self._outputs = OrderedDict()
    
    def set_input_type(self, type_or_parse):
        """ Set an unique input type.
        
        If you use this then you have only one input for the play.
        """
        self._inputs = OrderedDict()
        default_inputs = self.engine.in_name
        if len(default_inputs) > 1:
            raise ValueError("First block of the engine need more than one input, you sould use `add_inpout` for each of them")
        self.add_input(default_inputs[0], type_or_parse)

    def add_input(self, in_name, type_or_parse):
        """ declare a possible input
        """
        if not isinstance(type_or_parse, GenericType) and callable(type_or_parse):
            type_or_parse = GenericType(parse=type_or_parse)
        elif not isinstance(type_or_parse, GenericType):
            raise ValueError("the given 'type_or_parse' is invalid")
        self._inputs[in_name] = type_or_parse

    def set_outputs(self, outputs):
        """ :param outputs: dict {name: serializer} """
        if outputs is None:
            raise ValueError("Invalid outputs should not be none.")
        self._outputs = OrderedDict()
        for name, serializer in outputs.iteritems():
            self.add_output(name, serializer)
        
    def add_output(self, out_name, serializer=None):
        """ declare an output
        """
        if serializer is not None and not callable(serializer):
            raise ValueError("the given 'serializer' is invalid")
        self._outputs[out_name] = serializer

    
    def options(self):
        """ Engine options discover HTTP entry point
        """
        #configure engine with an empty dict to ensure default selection/options
        self.engine.configure({})
        conf = self.engine.as_dict()
        conf["returns"] = [oname for oname in self._outputs.iterkeys()]
        # Note: we overide args to only list the ones that are declared in this view
        conf["args"] = [iname for iname in self._inputs.iterkeys()]
        return jsonify(conf)

    
    def play(self):
        """ Main http entry point: run the reliure engine
        """
        data, options = parse_request(request)
        #warning: 'date' are the raw data from the client, not the de-serialised ones
        outputs = run_engine(self, data, options)
        return jsonify(outputs)

class ReliureFlaskView(Blueprint):
    """ Standart Flask json API view over a Reliure :class:`.Engine`.

    This is a Flask Blueprint (see http://flask.pocoo.org/docs/blueprints/)

    Here is a simple usage exemple:

    >>> from reliure.engine import Engine
    >>> from reliure import Composable
    >>> engine = Engine()
    >>> engine.requires("process")
    >>> engine.process.setup(in_name="in", out_name="out")
    >>> # setup the block's component
    >>> engine.process.append(Composable(lambda x: x**2))
    >>> 
    >>> ## create the API blue print
    >>> from reliure.utils.web import ReliureFlaskView
    >>> from reliure.types import Numeric
    >>> api = ReliureFlaskView()
    >>> # configure input/output
    >>> api.set_input_type(Numeric())
    >>> api.add_output("out")
    >>> 
    >>> # here you get your blueprint
    >>> # you can register it to your app with
    >>> app.register_blueprint(api, url_prefix="/api")    # doctest: +SKIP

    Then you will have two routes:
    
    - /api/options: it will provide a json that desctibe your api (ie your engine)
    - /api/play: used to run the engine itself
    
    To use the "play" entry point you can do :
    
    >>> request = {
    ...     "in": 5,       # this is the name of my input
    ...     "options": {}   # this this the api/engine configuration
    ... }
    >>> res = requests.get(
    ...     SERVER_URL+"/api/play",
    ...     data=json.dumps(request),
    ...     headers={"content-type": "application/json"}
    ... )                                                       # doctest: +SKIP
    >>> data = res.json()                                       # doctest: +SKIP
    {
        meta: ...
        results: {
            "out": 25
        }
    }
    """
    def __init__(self, expose_route=True, **kwargs):
        """ Build the Blueprint view over a :class:`.Engine`.
    
        :param engine: the reliure engine to serve through an json API
        :type engine: :class:`.Engine`.
        """
        super(ReliureFlaskView, self).__init__(repr(self), __name__, **kwargs)
        self.funcs = {}
        self.expose_route = expose_route

    
    def __repr__(self):
        return self.name

    
    def register(self, app, options, first_registration=False):
        if self.expose_route:
            self.add_url_rule('/', 'routes', lambda : self.routes(app) ,  methods=["GET"])
        super(ReliureFlaskView, self).register(app, options, first_registration=first_registration)
        
    #def add_url_rule(self, "/complete/<string:text>", 'complete', self.complete,  methods=["GET"])
    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        self.funcs[endpoint] = view_func
        super(ReliureFlaskView, self).add_url_rule( rule, endpoint, view_func , **options)

    def routes(self, app):
        #for rule in app.url_map.iter_rules():
        _routes = []
        for rule in app.url_map.iter_rules() :
            if str(rule).startswith(self.url_prefix):
                _routes.append( { 'path':rule.rule,
                                  'name':rule.endpoint,
                                  'methods':list(rule.methods)
                            })
        return jsonify({ 'api': self.name, 'routes': _routes })


    def add_engine(self, path, engine):
        # bind entry points
        self.add_url_rule('/engine/%s' % path, path, engine.options,  methods=["GET"])
        self.add_url_rule('/engine/%s/options' % path,  '%s_options' %path, engine.options,  methods=["GET"])
        self.add_url_rule('/engine/%s/play' % path, '%s_play' %path, engine.play,  methods=["POST", "GET"])


    def call(self, endpoint, *args, **kwargs):
        return self.funcs[endpoint](*args, **kwargs)
        

class RemoteApi(Blueprint):
    def __init__(self, url ):
        """ Function doc
        :param url: engine api url
        """
        print "RemoteApi @ %s" % url
        resp = requests.get(url)
        api = json.loads(resp.content)
        
        super(RemoteApi, self).__init__(api['api'], __name__)
        self.url = url
        self.name = api['api']

        # XXXX very moche
    
        for route in api['routes']:
            endpoint = route['name'].split('.')[-1]
            methods = route['methods']
            s =  route['path'].split('/')[1:]
            
            print ">>>>>>" , route['path'], s
            def get( *args, **kwargs):
                print "http_get", endpoint
                return self.http_get("/%s" % endpoint, *args, **kwargs)
            
            if 'engine' in s:
                if not 'play' in s and not 'options' in s :
                    path = "/%s" % "/".join(s)
                    http_path = "/%s" % "/".join(s[1:])
                    print "RemoteApi init engine", path, endpoint
                    self.add_url_rule( path,  endpoint, lambda : self.http_get(http_path))
                    self.add_url_rule( "%s/options"% path, "%s_options"% endpoint, lambda : self.http_get(http_path))
                    self.add_url_rule( "%s/play"% path, "%s_play"% endpoint, lambda: self.play(http_path),  methods=['GET','POST'])
            elif 'engine' in s:
                pass
            else :
                print "RemoteApi init", path, endpoint
                self.add_url_rule( route['path'],  endpoint, get)

    
    def __repr__(self):
        return self.name


    def register(self, app, options, first_registration=False):
        #self.add_url_rule('/%s' %self.name , 'routes', lambda : self.routes(app) ,  methods=["GET"])
        super(RemoteApi, self).register(app, options, first_registration=first_registration)
        

    def routes(self, app):
        #for rule in app.url_map.iter_rules():
        _routes = []
        for rule in app.url_map.iter_rules() :
            if str(rule).startswith(self.url_prefix):
                _routes.append( { 'path':rule.rule,
                                  'name':rule.endpoint,
                                  'methods':list(rule.methods)
                            })
        return jsonify({ 'api': self.name, 'routes': _routes })



    def call(self, endpoint, *args, **kwargs):
        return self.http_get("/"+endpoint, *args, **kwargs)
        
    def http_get(self, path, *args, **kwargs):
        """ Function doc
        :param : 
        """
        _path = "/".join( [ p for p in ([ path ] + list(kwargs.values())) if p not in (None, "") ] )
        url = '%s%s'% ( self.url, _path ) 
        resp = requests.get(url)
        data = json.loads(resp.content)
        return jsonify(data)
        
    def play(self, path):
        """ Function doc
        :param : 
        """
        if request.headers['Content-Type'].startswith('application/json'):
            # data in JSON
            data = request.json
            url = '%s%s/play'% (self.url,path)
            resp = requests.post(url, json=data)
            data = json.loads(resp.content)
            return jsonify(data)
        return 404 # XXX

