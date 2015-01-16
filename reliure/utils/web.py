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

from reliure import Composable
from reliure.types import GenericType, Text
from reliure.exceptions import ReliurePlayError
from reliure.engine import Engine, Block

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
    """ View over an :class:`.Engine` or a :class:`.Block`
    
    >>> engine = Engine("count_a", "count_b")
    >>>
    >>> engine.count_a.setup(in_name='in')
    >>> engine.count_a.set(lambda chaine: chaine.count("a"))
    >>>
    >>> engine.count_b.setup(in_name='in')
    >>> engine.count_b.set(lambda chaine: chaine.count("b"))
    >>> 
    >>> 
    >>> # we can build a view on this engine
    >>> egn_view = EngineView(engine, name="count")
    >>> egn_view.add_output("count_a")  # note that by default block outputs are named by block's name
    >>> egn_view.add_output("count_b")
    >>> # one can specify a short url for this engine
    >>> egn_view.get("/q/<in>")
    >>>
    >>> # this view can be added to a reliure API
    >>> api = ReliureJsonAPI("api")
    >>> api.plug(egn_view)
    """
    def __init__(self, engine, name=None):
        self.engine = engine
        self.name = name
        self._short_route = None
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
            raise ValueError("Need more than one input, you sould use `add_inpout` for each of them")
        self.add_input(default_inputs[0], type_or_parse)

    def inputs(*args, **kwargs):
        """ Set the inputs
        """
        for in_name in args:
            self.add_input(in_name)
        for in_name, type_or_parse in kwargs.iteritems():
            self.add_output(in_name, type_or_parse)

    def add_input(self, in_name, type_or_parse=None):
        """ declare a possible input
        """
        if type_or_parse is None:
            type_or_parse = GenericType()
        elif not isinstance(type_or_parse, GenericType) and callable(type_or_parse):
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
        if type_or_serialize is None:
            type_or_serialize = GenericType()
        if not isinstance(type_or_serialize, GenericType) and callable(type_or_serialize):
            type_or_serialize = GenericType(serialize=type_or_serialize)
        elif not isinstance(type_or_serialize, GenericType):
            raise ValueError("the given 'type_or_serialize' is invalid")
        self._outputs[out_name] = type_or_serialize

    def get(self, route):
        self._short_route = route

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
            # TODO: manage config/data in url
    #            args = request.args
    #            if args.get('_f') == 'semicolons':
    #                pairs = args.get('q').split(',')
    #                data['query'] = dict( tuple(x.split(':')) for x in pairs ) 

        #TODO: parse data according to self._inputs
        # note: all the inputs can realy be parsed only if the engine is setted
        return data, options

    def run(self, inputs_data, options):
        """ Run the engine/block according to some inputs data and options
        
        It is called from :func:`play`
        
        :param inputs_data: dict of input data
        :param options: engine/block configuration dict
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
        if not all(inname in self._inputs for inname in needed_inputs):
            #Note: this may be check staticly
            missing = [inname for inname in needed_inputs if inname not in self._inputs]
            raise ValueError("With this configuration the inputs %s are needed but not declared." % missing)
        # check if all inputs are given
        if not all(inname in inputs_data for inname in needed_inputs):
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
        """ Main http entry point: run the engine
        """
        data, options = self.parse_request(request)
        #warning: 'date' are the raw data from the client, not the de-serialised ones
        outputs = self.run(data, options)
        return jsonify(outputs)

    def short_play(self, **kwargs):
        """ Main http entry point: run the engine
        """
        options = {}
        outputs = self.run(kwargs, options)
        return jsonify(outputs)


class ComponentView(EngineView):
    """ View over a simple component (:class:`.Composable` or simple function)
    """
    def __init__(self, component):
        if not isinstance(component, Composable):
            if callable(component):
                component = Composable(component)
            else:
                raise ValueError("component '%s' is not Optionable nor Composable and even not callable" % component)
        blk_name = component.name
        self._blk = Block(component.name)
        self._blk.set(component)
        
        super(ComponentView, self).__init__(self._blk, blk_name)

    def add_input(self, in_name, type_or_parse=None):
        self._blk.setup(in_name=in_name)
        #XXX: ca ne va pas si multiple input
        super(ComponentView, self).add_input(in_name, type_or_parse)

    def add_output(self, out_name, type_or_serialize=None):
        self._blk.setup(out_name=out_name)
        #XXX: attention il faut interdire les multi output
        super(ComponentView, self).add_output(out_name, type_or_serialize)


class ReliureJsonAPI(Blueprint):
    """ Standart Flask json API view over a Reliure :class:`.Engine`.

    This is a Flask Blueprint (see http://flask.pocoo.org/docs/blueprints/)

    Here is a simple usage exemple:

    >>> from reliure.engine import Engine
    >>> engine = Engine("process")
    >>> engine.process.setup(in_name="in", out_name="out")
    >>> # setup the block's component
    >>> engine.process.set(lambda x: x**2)
    >>> 
    >>> # configure a view for the engine
    >>> egn_view = EngineView(engine)
    >>> # configure view input/output
    >>> from reliure.types import Numeric
    >>> egn_view.set_input_type(Numeric())
    >>> egn_view.add_output("out")
    >>> 
    >>> ## create the API blueprint
    >>> api = ReliureJsonAPI()
    >>> api.plug(egn_view, url_prefix="egn")
    >>>
    >>> # here you get your blueprint
        for name, serializer in outputs.iteritems():
    >>> # you can register it to your app with
    >>> app.register_blueprint(api, url_prefix="/api")    # doctest: +SKIP

    Then you will have two routes:
    
    - [GET] /api/: returns a json that desctibe your api routes
    - [GET] /api/egn: returns a json that desctibe your engine
    - [POST] /api/egn: run the engine itself

    To use the "POST" entry point you can do :

    >>> request = {
    ...     "in": 5,       # this is the name of my input
    ...     "options": {}   # this this the api/engine configuration
    ... }
    >>> res = requests.get(
    ...     SERVER_URL+"/api/egn",
    ...     data=json.dumps(request),
    ...     headers={"content-type": "application/json"}
    ... )                                                       # doctest: +SKIP
    >>> data = res.json()                                       # doctest: +SKIP
    {
        meta: {...}
        results: {
            "out": 25
        }
    }
    """
    def __init__(self, name="api", url_prefix=None, **kwargs):
        """ Build the Blueprint view over a :class:`.Engine`.
    
        :param name: the name of this api (used as url prefix by default)
        """
        assert isinstance(name, basestring)
        # set url_prefix from name if not setted
        if url_prefix is None:
            url_prefix = "/%s" % name
        super(ReliureJsonAPI, self).__init__(name, __name__, url_prefix=url_prefix, **kwargs)
        self.name = name
        self.expose_route = True
        #Note: the main get "/" route exposition is binded in register method

    def __repr__(self):
        return self.name

    def plug(self, view, url_prefix=None):
        """ Associate a :class:`EngineView` to this api
        """
        if url_prefix is None:
            if view.name is None:
                raise ValueError("EngineView has no name and path is not specified")
            url_prefix = view.name
        # bind entry points
        self.add_url_rule('/%s' % url_prefix, '%s_options' % url_prefix, view.options, methods=["GET"])
        self.add_url_rule('/%s' % url_prefix, '%s_play' % url_prefix, view.play, methods=["POST"])
        # manage short route
        if view._short_route is not None:
            self.add_url_rule(
                '/%s/%s' % (url_prefix, view._short_route),
                '%s_short_play' % url_prefix,
                view.short_play, methods=["GET"]
            )

    def _routes(self, app):
        """ list of routes (you should have the app where this is register)
        """
        print "###########  route"
        _routes = []
        prefix = self.url_prefix if self.url_prefix is not None else ""
        for rule in app.url_map.iter_rules():
            if str(rule).startswith(prefix):
                _routes.append({
                    'path':rule.rule,
                    'name':rule.endpoint,
                    'methods':list(rule.methods)
                })
        returns = {
            'api': self.name,
            'url_root': request.url_root,
            'routes': _routes
        }
        print returns
        return jsonify(returns)

    def register(self, app, options, first_registration=False):
        # Note: the main api route '/' is added here because one know to have the
        # app to get all the routes
        if self.expose_route:
            ## add the main api route
            self.add_url_rule('/', 'routes', lambda: self._routes(app), methods=["GET"])
        super(ReliureJsonAPI, self).register(app, options, first_registration=first_registration)


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
