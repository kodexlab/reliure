#-*- coding:utf-8 -*-
import unittest

import json
from flask import Flask

from reliure.pipeline import Optionable
from reliure.engine import Engine
from reliure.types import Numeric
from reliure.exceptions import ValidationError

from reliure.web import ReliureAPI, EngineView, ComponentView

class OptProductEx(Optionable):
    def __init__(self, name="mult_opt"):
        super(OptProductEx, self).__init__(name)
        self.add_option("factor", Numeric(default=5, help="multipliation factor", vtype=int))

    def __call__(self, arg, factor=5):
        return arg * factor


class TestReliureAPISimple(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.engine = Engine("op1", "op2")
        self.engine.op1.setup(in_name="in")
        self.engine.op2.setup(out_name="out")

        self.engine.op1.set(OptProductEx())

        foisdouze = OptProductEx("foisdouze")
        foisdouze.force_option_value("factor", 12)
        self.engine.op2.set(foisdouze, OptProductEx())

        egn_view = EngineView(self.engine)
        egn_view.set_input_type(Numeric(vtype=int, min=-5, max=5))
        egn_view.add_output("out")

        api = ReliureAPI()
        api.register_view(egn_view, url_prefix="egn")

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api, url_prefix="/api")
        self.app = app.test_client()

    def test_routes(self):
        resp = self.app.get('api/')
        data = json.loads(resp.data)
        assert data == {
            u'api': u'api',
            u'routes': [
                {
                    u'methods': [u'HEAD', u'OPTIONS', u'GET'],
                    u'name': u'api.egn_options',
                    u'path': u'/api/egn'
                },
                {
                    u'methods': [u'POST', u'OPTIONS'],
                    u'name': u'api.egn',
                    u'path': u'/api/egn'
                },
                {
                    u'methods': [u'HEAD', u'OPTIONS', u'GET'],
                    u'name': u'api.routes',
                    u'path': u'/api/'
                }
            ],
            u'url_root': u'http://localhost/'
        }

    def test_options(self):
        resp = self.app.get('api/egn')
        data = json.loads(resp.data)
        # check we have the same than in engine
        assert data["blocks"] == self.engine.as_dict()["blocks"]
        assert data["args"] == ["in"]
        assert data["returns"] == ["out"]

    def test_play_simple(self):
        # prepare query
        rdata = {'in': '2'}
        json_data = json.dumps(rdata)
        resp = self.app.post('api/egn', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert "out" in results
        assert len(results) == 1
        assert results["out"] == 2*5*12

    def test_play_fail(self):
        json_data = json.dumps({'in': 10})
        # max is 5, so validation error
        with self.assertRaises(ValidationError):
            resp = self.app.post('api/egn', data=json_data, content_type='application/json')

        json_data = json.dumps({'in': "chat"})
        # parsing error
        with self.assertRaises(ValueError):
            resp = self.app.post('api/egn', data=json_data, content_type='application/json')

        json_data = json.dumps({'in': 1})
        resp = self.app.post('api/egn', data=json_data)
        # error 415 "Unsupported Media Type" see:
        # http://en.wikipedia.org/wiki/List_of_HTTP_status_codes#4xx_Client_Error
        assert resp.status_code == 415

    def test_play_simple_options(self):
        # prepare query
        rdata = {'in': 2}
        rdata["options"] = {
            'op2': [{
                'name': 'mult_opt',
                'options': {
                    'factor': '2'
                }
            }]
        }
        json_data = json.dumps(rdata)
        resp = self.app.post('api/egn', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert "out" in results
        assert len(results) == 1
        assert results["out"] == 2*2*5


class TestReliureAPIMultiInputs(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.engine = Engine("op1", "op2")
        self.engine.op1.setup(in_name="in", out_name="middle", required=False)
        self.engine.op2.setup(in_name="middle", out_name="out")

        self.engine.op1.set(OptProductEx())
        foisdouze = OptProductEx("foisdouze")
        foisdouze.force_option_value("factor", 12)
        self.engine.op2.set(foisdouze, OptProductEx())

        egn_view = EngineView(self.engine, name="my_egn")
        egn_view.add_input("in", Numeric(vtype=int, min=-5, max=5))
        egn_view.add_input("middle", Numeric(vtype=int))
        egn_view.add_output("in")
        egn_view.add_output("middle")
        egn_view.add_output("out")

        api = ReliureAPI()
        api.register_view(egn_view)

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api, url_prefix="/api")
        self.app = app.test_client()

    def test_routes(self):
        resp = self.app.get('api/')
        data = json.loads(resp.data)
        assert data == {
            u'api': u'api',
            u'routes': [
                {
                    u'methods': [u'HEAD', u'OPTIONS', u'GET'],
                    u'name': u'api.my_egn_options',
                    u'path': u'/api/my_egn'
                },
                {
                    u'methods': [u'POST', u'OPTIONS'],
                    u'name': u'api.my_egn',
                    u'path': u'/api/my_egn'
                },
                {
                    u'methods': [u'HEAD', u'OPTIONS', u'GET'],
                    u'name': u'api.routes',
                    u'path': u'/api/'
                }
            ],
            u'url_root': u'http://localhost/'
        }

    def test_options(self):
        resp = self.app.get('api/my_egn')
        data = json.loads(resp.data)
        # check we have the same than in engine
        assert data["blocks"] == self.engine.as_dict()["blocks"]
        assert data["args"] == ["in", "middle"]
        assert data["returns"] == ["in", "middle", "out"]

    def test_play_simple(self):
        # it should be possible to play the full engine
        # prepare query
        rdata = {'in': 2}
        rdata["options"] = {
            'op1': [{
                'name': 'mult_opt',
            }]
        }
        json_data = json.dumps(rdata)
        resp = self.app.post('api/my_egn', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert "out" in results
        assert len(results) == 3 # in, middle, out
        assert results["out"] == 2*5*12

    def test_play_skip_op1(self):
        # it should be possible to play the only the block op2
        # prepare query
        rdata = {'middle': 2}
        rdata["options"] = {
            'op1': []
        }
        json_data = json.dumps(rdata)
        resp = self.app.post('api/my_egn', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert "out" in results
        assert len(results) == 2 # middle, out
        assert results["out"] == 2*12

        #TODO: test error when wrong input


class TestReliureAPIWithBlock(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.engine = Engine("op1", "op2")
        self.engine.op1.setup(in_name="in", out_name="middle")
        self.engine.op2.setup(in_name="middle", out_name="out")

        self.engine.op1.set(OptProductEx())

        foisdouze = OptProductEx("foisdouze")
        foisdouze.force_option_value("factor", 12)
        foisquatre = OptProductEx("foisquatre")
        foisquatre.force_option_value("factor", 4)
        self.engine.op2.set(foisdouze, foisquatre)

        op2_view = EngineView(self.engine.op2, name="op2")
        op2_view.set_input_type(Numeric(vtype=int))
        op2_view.add_output("out")

        api = ReliureAPI()
        api.register_view(op2_view)

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api, url_prefix="/api")
        self.app = app.test_client()

    def test_options(self):
        resp = self.app.get('api/op2')
        data = json.loads(resp.data)
        # check we have the same than in engine
        assert data["components"] == self.engine.op2.as_dict()["components"]
        assert data["args"] == ["middle"]
        assert data["returns"] == ["out"]

    def test_play_simple(self):
        # it should be possible to play the full engine
        # prepare query
        rdata = {'middle': 2}
        rdata["options"] = {
            'name': 'foisquatre',
        }
        json_data = json.dumps(rdata)
        resp = self.app.post('api/op2', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert "out" in results
        assert len(results) == 1 # in, middle, out
        assert results["out"] == 2*4


class TestComponentView(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        comp_view = ComponentView(OptProductEx())
        comp_view.add_input("number", Numeric())
        comp_view.add_output("value", Numeric())
        comp_view.get("n/<number>")

        api = ReliureAPI()
        api.register_view(comp_view)

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api, url_prefix="/api")
        self.app = app.test_client()

    def test_routes(self):
        resp = self.app.get('api/')
        data = json.loads(resp.data)
        assert data == {
            u'routes': [
                {
                    u'path': u'/api/mult_opt',
                    u'name': u'api.mult_opt_options',
                    u'methods': [u'HEAD', u'OPTIONS', u'GET']
                },
                {
                    u'path': u'/api/mult_opt',
                    u'name': u'api.mult_opt',
                    u'methods': [u'POST', u'OPTIONS']
                },
                {
                    u'path': u'/api/',
                    u'name': u'api.routes',
                    u'methods': [u'HEAD', u'OPTIONS', u'GET']
                },
                {
                    u'path': u'/api/mult_opt/n/<number>',
                    u'name': u'api.mult_opt_short_play',
                    u'methods': [u'HEAD', u'OPTIONS', u'GET']
                },
            ],
            u'url_root': u'http://localhost/',
            u'api': u'api'
        }

    def test_options(self):
        resp = self.app.get('api/mult_opt')
        data = json.loads(resp.data)
        print data
        # check we have the same than in engine
        assert data == {
            u'required': True,
            u'multiple': False,
            u'name': u'mult_opt',
            u'args': [u'number'],
            u'returns': [u'value'],
            u'components': [
                {
                    u'default': True,
                    u'name': u'mult_opt', 
                    u'options': [
                        {
                            u'otype': {
                                u'multi': False,
                                u'vtype': u'int',
                                u'help': u'multipliation factor',
                                u'min': None,
                                u'default': 5,
                                u'max': None,
                                u'choices': None,
                                u'uniq': False,
                                u'type': u'Numeric'
                            },
                            u'type': u'value',
                            u'name': u'factor',
                            u'value': 5
                        }
                    ]
                }
            ]
        }

    def test_play_simple(self):
        # prepare query
        rdata = {
            'number': 3,
            'options': {
                'name': 'mult_opt',
                'options': {
                    'factor': 2,
                }
            }
        }
        json_data = json.dumps(rdata)
        resp = self.app.post('api/mult_opt', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert results == {"value": 2*3}

    def test_play_short(self):
        resp = self.app.get('api/mult_opt/n/33', content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        assert "results" in resp_data
        results = resp_data["results"]
        assert results == {"value": 33*5}

