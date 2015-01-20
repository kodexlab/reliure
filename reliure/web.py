#-*- coding:utf-8 -*-
""" :mod:`reliure.web`
======================

helpers to build HTTP/Json Api from reliure engines
"""

import sys
import json
import requests
import logging

from collections import OrderedDict

from flask import Flask, Blueprint
from flask import abort, request, jsonify

from reliure import Composable
from reliure.types import GenericType, Text
from reliure.exceptions import ReliurePlayError
from reliure.engine import Engine, Block

# for error code see http://fr.wikipedia.org/wiki/Liste_des_codes_HTTP#Erreur_du_client

__all__ = ["app_routes", "EngineView", "ComponentView", "ReliureAPI", "RemoteApi"]

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
    >>> egn_view.play_route("/q/<in>")
    >>>
    >>> # this view can be added to a reliure API
    >>> api = ReliureAPI("api")
    >>> api.register_view(egn_view)
    """
    def __init__(self, engine, name=None):
        self._logger = logging.getLogger("reliure.%s" % self.__class__.__name__)
        self.engine = engine
        self.name = name
        self._short_routes = []
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
            raise ValueError("Need more than one input, you sould use `add_input` for each of them")
        self.add_input(default_inputs[0], type_or_parse)

    def add_input(self, in_name, type_or_parse=None):
        """ Declare a possible input
        """
        if type_or_parse is None:
            type_or_parse = GenericType()
        elif not isinstance(type_or_parse, GenericType) and callable(type_or_parse):
            type_or_parse = GenericType(parse=type_or_parse)
        elif not isinstance(type_or_parse, GenericType):
            raise ValueError("the given 'type_or_parse' is invalid")
        self._inputs[in_name] = type_or_parse

    def set_outputs(self, *outputs):
        """ Set the outputs of the view
        """
        self._outputs = OrderedDict()
        for output in outputs:
            out_name = None
            type_or_serialize = None
            if isinstance((list, tuple), output):
                if len(output) == 1:
                    out_name = output[0]
                elif len(output) == 2:
                    out_name = output[0]
                    type_or_serialize = output[1]
                else:
                    raise ValueError("invalid output format")
            else:
                out_name = output
            self.add_output(out_name, type_or_serialize)

    def add_output(self, out_name, type_or_serialize=None):
        """ Declare an output
        """
        if type_or_serialize is None:
            type_or_serialize = GenericType()
        if not isinstance(type_or_serialize, GenericType) and callable(type_or_serialize):
            type_or_serialize = GenericType(serialize=type_or_serialize)
        elif not isinstance(type_or_serialize, GenericType):
            raise ValueError("the given 'type_or_serialize' is invalid")
        self._outputs[out_name] = type_or_serialize

    def play_route(self, *routes):
        """ Define routes for GET play.
        
        This use Flask route syntax, see:
        http://flask.pocoo.org/docs/0.10/api/#url-route-registrations
        """
        self._short_routes = routes

    def _config_from_url(self):
        """ Manage block configuration from requests.args (url params)
        
        May be overriden
        """
        self._logger.warn("_config_from_url not yet implemented for EngineView")
        return {}

    def parse_request(self):
        """ Parse request for :func:`play`
        """
        data = {}
        options = {}
        ### get data
        if request.headers['Content-Type'].startswith('application/json'):
            # data in JSON
            data = request.json
            assert data is not None #FIXME: better error than assertError ?
            if "options" in data:
                options = data["options"]
                del data["options"]
        else:
            # data in URL/post
            data = dict()
            data.update(request.form)
            data.update(request.args)
            for key, value in data.iteritems():
                if isinstance(value, list) and len(value) == 1:
                    data[key] = value[0]
            # manage config in url
            options = self._config_from_url()
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
            raise
            abort(406, err)  # Not Acceptable

        ### Check inputs
        needed_inputs = self.engine.needed_inputs()
        # add default
        for inname in needed_inputs:
            if inname not in inputs_data \
                    and inname in self._inputs \
                    and self._inputs[inname].default is not None:
                inputs_data[inname] = self._inputs[inname].default
        # check if all needed inputs are possible
        if not all(inname in self._inputs for inname in needed_inputs):
            #Note: this may be check staticly
            missing = [inname for inname in needed_inputs if inname not in self._inputs]
            raise ValueError("Inputs %s are needed but not declared." % missing)
        # check if all inputs are given
        if not all(inname in inputs_data for inname in needed_inputs):
            # configuration error
            missing = [inname for inname in needed_inputs if inname not in inputs_data]
            raise ValueError("Inputs %s are missing." % missing)
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
        data, options = self.parse_request()
        #warning: 'data' are the raw data from the client, not the de-serialised ones
        outputs = self.run(data, options)
        return jsonify(outputs)

    def short_play(self, **kwargs):
        """ Main http entry point: run the engine
        """
        # options in URL arguments
        config = self._config_from_url()
        outputs = self.run(kwargs, config)
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
        # default output name
        super(ComponentView, self).add_output(self._blk.out_name)
        self._default_out_name = True

    def add_input(self, in_name, type_or_parse=None):
        super(ComponentView, self).add_input(in_name, type_or_parse)
        # update the block inputs names
        self._blk.setup(in_name=self._inputs.keys())

    def add_output(self, out_name, type_or_serialize=None):
        if self._default_out_name:
            self._outputs = OrderedDict()
            self._default_out_name = False
        self._blk.setup(out_name=out_name)
        #XXX: attention il faut interdire les multi output
        super(ComponentView, self).add_output(out_name, type_or_serialize)

    def _config_from_url(self):
        """ Manage block configuration from requests.args (url params)
        """
        config = {
            "name": self._blk.name,
            "options": {}
        }
        for key, value in request.args.iteritems():
            if isinstance(value, list) and len(value) == 1:
                config["options"][key] = value[0]
            else:
                config["options"][key] = value
        return config


class ReliureAPI(Blueprint):
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
    >>> api = ReliureAPI()
    >>> api.register_view(egn_view, url_prefix="egn")
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
        self._logger = logging.getLogger("reliure.%s" % self.__class__.__name__)
        assert isinstance(name, basestring)
        # set url_prefix from name if not setted
        if url_prefix is None:
            url_prefix = "/%s" % name
        super(ReliureAPI, self).__init__(name, __name__, url_prefix=url_prefix, **kwargs)
        self.name = name
        self.expose_route = True
        #Note: the main get "/" route exposition is binded in register method

        #TODO add error handler

    def __repr__(self):
        return self.name

    def register_view(self, view, url_prefix=None):
        """ Associate a :class:`EngineView` to this api
        """
        if url_prefix is None:
            if view.name is None:
                raise ValueError("EngineView has no name and path is not specified")
            url_prefix = view.name
        # bind entry points
        self.add_url_rule('/%s' % url_prefix, '%s_options' % url_prefix, view.options, methods=["GET"])
        self.add_url_rule('/%s' % url_prefix, '%s' % url_prefix, view.play, methods=["POST"])
        # url
        self.add_url_rule('/%s/options' % url_prefix, '%s_options_OLD' % url_prefix, view.options, methods=["GET"])
        self.add_url_rule('/%s/play' % url_prefix, '%s_OLD' % url_prefix, view.play, methods=["POST"])

        # manage short route
        for route in view._short_routes:
            self.add_url_rule(
                '/%s/%s' % (url_prefix, route),
                '%s_short_play' % url_prefix,
                view.short_play, methods=["GET"]
            )

    def _routes(self, app):
        """ list of routes (you should have the app where this is register)
        """
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
        return jsonify(returns)

    def register(self, app, options, first_registration=False):
        # Note: the main api route '/' is added here because one know to have the
        # app to get all the routes
        if self.expose_route:
            ## add the main api route
            self.add_url_rule('/', 'routes', lambda: self._routes(app), methods=["GET"])
        super(ReliureAPI, self).register(app, options, first_registration=first_registration)


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

            self.add_url_rule( route['path'],  endpoint, self.forward, methods=methods)
            #if 'engine' in s:
                #if not 'play' in s and not 'options' in s :
                    #http_path = "/%s" % "/".join(s[1:])
                    #print "RemoteApi init engine", path, endpoint
                    #self.add_url_rule( "%s/options"% route['path'], "%s_options"% endpoint,self.forward)
                    #self.add_url_rule( "%s/play"% route['path'], "%s_play"% endpoint, self.forward,  methods=['GET','POST'])
            #elif 'engine' in s:
                #pass
            #else :
                #self.add_url_rule( "%s" % route['path'], "%s" % endpoint,self.forward)

        @self.errorhandler(405)
        def bad_request(error):
            msg = "errors 405 : request method allowed GET, POST' ", 405
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
        accept *ONLY* GET and POST
        """
        # rewrite url path  
        prefix = self.url_prefix
        path= "" if request.path == "/" else request.path
        path = path[len(prefix):]
        url = '%s%s'% ( self.url_root[:-1], path )

        print "FORWARDING to", url 
        
        if request.method == 'GET':
            resp = requests.get(url, params=request.args)
            data = json.loads(resp.content)
            return jsonify(data)
            
        elif request.method == 'POST':
            if request.headers['Content-Type'].startswith('application/json'):
                # data in JSON
                resp = requests.post(url, json=request.json)
                data = request.json
            else :
                resp = requests.post(url, json=request.form)
                data = request.form
    
            data = json.loads(resp.content)
            return jsonify(data)
                
                
        # method not allowed aborting
        abort(405) # XXX
