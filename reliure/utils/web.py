#-*- coding:utf-8 -*-
""" :mod:`reliure.utils.web`
============================

helpers to build HTTP/Json Api from reliure engines
"""

import sys
import json
import requests

from collections import OrderedDict

from flask import Flask, Blueprint
from flask import abort, request, jsonify

from reliure.types import GenericType, Text
from reliure.exceptions import ReliurePlayError
from reliure.engine import Engine

# for error code see http://fr.wikipedia.org/wiki/Liste_des_codes_HTTP#Erreur_du_client

def app_routes(app):
    """ list of route of an app
    """
    _routes = []
    for rule in app.url_map.iter_rules():
        _routes.append({
            'path': rule.rule,
            'name': rule.endpoint,
            'methods': list(rule.methods)
        })
    return jsonify({'routes': _routes})


class EngineView(object):
    def __init__(self, engine):
        self.engine = engine
        # default input
        self._inputs = OrderedDict()
        # default outputs
        self._outputs = OrderedDict()

    def inputs(*args, **kwargs):
        """ Set the inputs
        """
        for in_name in args:
            self.add_input(in_name)
        for in_name, type_or_parse in kwargs.iteritems():
            self.add_output(in_name, type_or_parse)

    def add_input(self, in_name, type_or_parse):
        """ declare a possible input
        """
        if not isinstance(type_or_parse, GenericType) and callable(type_or_parse):
            type_or_parse = GenericType(parse=type_or_parse)
        elif not isinstance(type_or_parse, GenericType):
            raise ValueError("the given 'type_or_parse' is invalid")
        self._inputs[in_name] = type_or_parse

    def returns(*args, **kwargs):
        """ Set the serialized outputs
        """
        for out_name in args:
            self.add_output(out_name)
        for out_name, type_or_serialize in kwargs.iteritems():
            self.add_output(out_name, type_or_serialize)

    def add_output(self, out_name, type_or_serialize=None):
        """ declare an output
        """
        if not isinstance(type_or_serialize, GenericType) and callable(type_or_serialize):
            type_or_serialize = GenericType(serialize=type_or_serialize)
        elif not isinstance(type_or_serialize, GenericType):
            raise ValueError("the given 'type_or_serialize' is invalid")
        self._outputs[out_name] = type_or_serialize

    def parse_request(self, request):
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

    def run_engine(self, inputs_data, options):
        """ Run the engine according to some inputs data and options
        """
        ### configure the engine
        try:
            self.engine.configure(options)
        except ValueError as err:
            #TODO beter manage input error: indicate what's wrong
            abort(406)  # Not Acceptable

        ### Check inputs
        needed_inputs = self.engine.needed_inputs()
        # check if all needed inputs are possible
        if not all([inname in self._inputs for inname in needed_inputs]):
            #Note: this may be check staticly
            missing = [inname for inname in needed_inputs if inname not in self._inputs]
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
            input_val = self._inputs[inname].parse(inputs_data[inname])
            self._inputs[inname].validate(input_val)
            inputs[inname] = input_val
        #
        ### run the engine
        error = False # by default ok
        try:
            raw_res = self.engine.play(**inputs)
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
                if out_name not in self._outputs:
                    continue
                serializer = self._outputs[out_name].serialize
                # serialise output
                if serializer is not None:
                    results[out_name] = serializer(raw_res[out_name])
                else:
                    results[out_name] = raw_res[out_name]
        ### prepare the retourning json
        # add the results
        outputs["results"] = results
        ### serialise play metadata
        outputs['meta'] = self.engine.meta.as_dict()
        #note: meta contains the error (if any)
        return outputs

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
        data, options = self.parse_request(request)
        #warning: 'date' are the raw data from the client, not the de-serialised ones
        outputs = self.run_engine(data, options)
        return jsonify(outputs)


class ReliureJsonAPI(Blueprint):
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
        for name, serializer in outputs.iteritems():
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
    def __init__(self, name, expose_route=True, url_prefix=None, **kwargs):
        """ Build the Blueprint view over a :class:`.Engine`.
    
        :param engine: the reliure engine to serve through an json API
        :type engine: :class:`.Engine`.
        """
        # set url_prefix from name if not setted
        if url_prefix is None:
            url_prefix = "/%s" % name
        super(ReliureBlue, self).__init__(name, __name__, url_prefix=url_prefix, **kwargs)
        self.expose_route = expose_route
        self.name = name 

    def __repr__(self):
        return self.name

    def _routes(self, app):
        """ list of route for an API in a app
        """
        _routes = []
        prefix = ""  if self.url_prefix is None else self.url_prefix
        for rule in app.url_map.iter_rules():
            if str(rule).startswith(prefix):
                _routes.append({
                    'path':rule.rule,
                    'name':rule.endpoint,
                    'methods':list(rule.methods)
                })
        returns = {
            'api': self.name,
            'url_root' : request.url_root,
            'routes': _routes
        }
        return jsonify(returns)

    def plug(self, view, path=None):
        # bind entry points
        self.add_url_rule('/%s' % path, '%s_options' % path, view.options, methods=["GET"])
        self.add_url_rule('/%s' % path, '%s_play' % path, view.play, methods=["POST"])

    def register(self, app, options, first_registration=False):
        # Note: the main api route '/' is added here because one know to have the
        # app to get all the routes
        if self.expose_route:
            ## add the main api route
            self.add_url_rule('/', 'routes', lambda: self._routes(app), methods=["GET"])
        super(ReliureBlue, self).register(app, options, first_registration=first_registration)


class RemoteApi(Blueprint):
    """ Proxy to a remote :class:`ReliureJsonAPI`
    """

    def __init__(self, url, **kwargs):
        """ Function doc
        :param url: engine api url
        """
        print "RemoteApi @ %s" % url
        resp = requests.get(url)
        api = json.loads(resp.content)
        
        super(RemoteApi, self).__init__(api['api'], __name__, **kwargs)
        self.url = url
        self.url_root = api['url_root']
        self.name = api['api']
    
        for route in api['routes']:
            endpoint = route['name'].split('.')[-1]
            methods = route['methods']
            s =  route['path'].split('/')[2:]
            path = "/%s" % "/".join(s)
            print ">>>>>>" , route['path'],  endpoint, s

            if 'engine' in s:
                if not 'play' in s and not 'options' in s :
                    http_path = "/%s" % "/".join(s[1:])
                    print "RemoteApi init engine", path, endpoint
                    self.add_url_rule( route['path'],  endpoint, self.forward)
                    self.add_url_rule( "%s/options"% route['path'], "%s_options"% endpoint,self.forward)
                    self.add_url_rule( "%s/play"% route['path'], "%s_play"% endpoint, self.forward,  methods=['GET','POST'])
            elif 'engine' in s:
                pass
            else :
                self.add_url_rule( "%s" % route['path'], "%s" % endpoint,self.forward)

        @self.errorhandler(405)
        def bad_request(error):
            msg = "errors 405 : request method allowed GET, POST with 'Content-Type=application/json' ", 405
            print msg
            return msg
            
    def __repr__(self):
        return self.name

    # useless
    def add_url_rule(self, path, endpoint, *args, **kwargs):
        print "RULE", path , endpoint
        super(RemoteApi, self).add_url_rule(path, endpoint, *args, **kwargs)

    def register(self, app, options, first_registration=False):

        #self.add_url_rule('/' , 'routes', lambda : app_routes(app) ,  methods=["GET"])

        # override url_prefix if new is given to app.register_blueprint
        # url_prefix is needed for url forwarding
        if options:
            self.url_prefix = options.get('url_prefix', self.url_prefix)

        super(RemoteApi, self).register(app, options, first_registration=first_registration)
        
    def forward(self, **kwargs):
        """ remote http call to api endpoint 
        accept *ONLY* GET and POST requests avec un content-type=application/json
        """
        # rewrite url path  
        prefix = self.url_prefix
        path= "" if request.path == "/" else request.path
        path = path[len(prefix):]
        url = '%s%s'% ( self.url_root[:-1], path )
        
        if request.method == 'GET':
            resp = requests.get(url, params=request.args)
            data = json.loads(resp.content)
            return jsonify(data)
            
        if request.method == 'POST':
            if request.headers['Content-Type'].startswith('application/json'):
                # data in JSON
                resp = requests.post(url, json=request.json)
                data = json.loads(resp.content)
                return jsonify(data)
                
        # method not allowed aborting
        abort(405) # XXX
