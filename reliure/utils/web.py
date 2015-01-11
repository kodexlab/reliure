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
    >>> api = ReliureFlaskView(engine)
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
    def __init__(self, engine):
        """ Build the Blueprint view over a :class:`.Engine`.
        
        :param engine: the reliure engine to serve through an json API
        :type engine: :class:`.Engine`.
        """
        super(ReliureFlaskView, self).__init__(repr(self), __name__)
        self.engine = engine
        # default input
        self._inputs = OrderedDict()
        # default outputs
        self._outputs = OrderedDict()
        
        # bind entry points
        self.add_url_rule('/options', 'options', self.options)
        self.add_url_rule('/play', 'play', self.play,  methods=["POST", "GET"])

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
                serializer = self._outputs[out_name]
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

    def play(self):
        """ Main http entry point: run the reliure engine
        """
        data, options = self.parse_request()
        #warning: 'date' are the raw data from the client, not the de-serialised ones
        outputs = self.run_engine(data, options)
        return jsonify(outputs)



class RemoteEngineApi(Blueprint):
    def __init__(self, url):
        """ Function doc
        :param url: engine api url
        """
        super(RemoteEngineApi, self).__init__(repr(self), __name__)

        self.url = url
        self.add_url_rule('/options', 'options', self.options)
        self.add_url_rule('/play', 'play', self.play,  methods=["POST", "GET"])
        
    def options(self):
        """ Function doc
        :param : 
        """
        resp = requests.get('%s/options'% self.url)
        data = json.loads(resp.content)
        return jsonify(data)
        
    def play(self):
        """ Function doc
        :param : 
        """
        if request.headers['Content-Type'].startswith('application/json'):
            # data in JSON
            data = request.json
            resp = requests.post('%s/play'% self.url, json=data)
            data = json.loads(resp.content)
            return jsonify(data)
        return 404 # XXX
                

        
        
        