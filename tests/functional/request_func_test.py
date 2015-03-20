"""
Request related funcational tests
"""

import datetime
import unittest
import urlparse
import StringIO

from dateutil.tz import tzutc
import httpretty
import pytest

from bravado.client import SwaggerClient
from bravado.compat import json
from tests.functional.conftest import register_spec, API_DOCS_URL, register_get


def test_form_params_in_request(httprettified, swagger_dict):
    param1_spec = {
        "in": "formData",
        "name": "param_id",
        "type": "integer"
    }
    param2_spec = {
        "in": "formData",
        "name": "param_name",
        "type": "string"
    }
    path_spec = swagger_dict['paths']['/test_http']
    path_spec['post'] = path_spec.pop('get')
    path_spec['post']['parameters'] = [param1_spec, param2_spec]
    register_spec(swagger_dict)
    httpretty.register_uri(httpretty.POST, "http://localhost/test_http?")
    resource = SwaggerClient.from_url(API_DOCS_URL).api_test
    resource.testHTTP(param_id=42, param_name='foo').result()
    content_type = httpretty.last_request().headers['content-type']
    assert 'application/x-www-form-urlencoded' == content_type
    body = urlparse.parse_qs(httpretty.last_request().body)
    assert {'param_name': ['foo'], 'param_id': ['42']} == body


def test_file_upload_in_request(httprettified, swagger_dict):
    param1_spec = {
        "in": "formData",
        "name": "param_id",
        "type": "integer"
    }
    param2_spec = {
        "in": "formData",
        "name": "file_name",
        "type": "file"
    }
    path_spec = swagger_dict['paths']['/test_http']
    path_spec['post'] = path_spec.pop('get')
    path_spec['post']['parameters'] = [param1_spec, param2_spec]
    path_spec['post']['consumes'] = ['multipart/form-data']
    register_spec(swagger_dict)
    httpretty.register_uri(httpretty.POST, "http://localhost/test_http?")
    resource = SwaggerClient.from_url(API_DOCS_URL).api_test
    resource.testHTTP(param_id=42, file_name=StringIO.StringIO('boo')).result()
    content_type = httpretty.last_request().headers['content-type']

    assert content_type.startswith('multipart/form-data')
    assert "42" in httpretty.last_request().body
    assert "boo" in httpretty.last_request().body


def test_parameter_in_path_of_request(httprettified, swagger_dict):
    path_param_spec = {
        "in": "path",
        "name": "param_id",
        "type": "string"
    }
    paths_spec = swagger_dict['paths']
    paths_spec['/test_http/{param_id}'] = paths_spec.pop('/test_http')
    paths_spec['/test_http/{param_id}']['get']['parameters'].append(
        path_param_spec)
    register_spec(swagger_dict)
    register_get('http://localhost/test_http/42?test_param=foo')
    resource = SwaggerClient.from_url(API_DOCS_URL).api_test
    resp = resource.testHTTP(test_param="foo", param_id="42").result()
    assert (200, None) == resp


def test_default_value_in_request(httprettified, swagger_dict):
    swagger_dict['paths']['/test_http']['get']['parameters'][0]['default'] = 'X'
    register_spec(swagger_dict)
    register_get("http://localhost/test_http?")
    resource = SwaggerClient.from_url(API_DOCS_URL).api_test
    resource.testHTTP().result()
    assert ['X'] == httpretty.last_request().querystring['test_param']


def test_array_with_collection_format_in_path_of_request(
        httprettified, swagger_dict):
    path_param_spec = {
        'in': 'path',
        'name': 'param_ids',
        'type': 'array',
        'items': {
            'type': 'integer'
        },
        'collectionFormat': 'csv',
    }
    swagger_dict['paths']['/test_http/{param_ids}'] = swagger_dict['paths'].pop('/test_http')
    swagger_dict['paths']['/test_http/{param_ids}']['get']['parameters'] = [path_param_spec]
    register_spec(swagger_dict)
    register_get('http://localhost/test_http/40,41,42')
    resource = SwaggerClient.from_url(API_DOCS_URL).api_test
    assert (200, None) == resource.testHTTP(param_ids=[40, 41, 42]).result()


class ResourceOperationTest(unittest.TestCase):
    def setUp(self):
        self.parameter = {
            "paramType": "query",
            "name": "test_param",
            "type": "string"
        }
        operation = {
            "method": "GET",
            "nickname": "testHTTP",
            "type": "void",
            "parameters": [self.parameter]
        }
        api = {
            "path": "/test_http",
            "operations": [operation]
        }
        self.response = {
            "swaggerVersion": "1.2",
            "basePath": "/",
            "apis": [api]
        }

    def register_urls(self):
        httpretty.register_uri(
            httpretty.GET, "http://localhost/api-docs",
            body=json.dumps({
                "swaggerVersion": "1.2",
                "apis": [{
                    "path": "/api_test"
                }]
            }))
        httpretty.register_uri(
            httpretty.GET, "http://localhost/api-docs/api_test",
            body=json.dumps(self.response))


    # ######################################################
    # # Validate paramType of parameters - path, query, body
    # ######################################################
    #
    # @httpretty.activate
    # def test_error_on_get_with_wrong_type_in_query(self):
    #     query_parameter = {
    #         "paramType": "query",
    #         "name": "test_param",
    #         "type": "integer"
    #     }
    #     self.response["apis"][0]["operations"][0]["parameters"] = [
    #         query_parameter]
    #     self.register_urls()
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     self.assertRaises(TypeError, resource.testHTTP,
    #                       test_param="NOT_INTEGER")
    #
    # @httpretty.activate
    # def test_error_on_get_with_array_type_in_query(self):
    #     query_parameter = {
    #         "paramType": "query",
    #         "name": "test_param",
    #         "type": "array",
    #         "items": {"type": "string"}
    #     }
    #     self.response["apis"][0]["operations"][0]["parameters"] = [
    #         query_parameter]
    #     self.register_urls()
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     self.assertRaises(TypeError, resource.testHTTP, test_param=["A", "B"])
    #
    # @httpretty.activate
    # def test_no_error_on_not_passing_non_required_param_in_query(self):
    #     self.register_urls()
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     # No error should be raised on not passing test_param (not required)
    #     resource.testHTTP()
    #
    # @httpretty.activate
    # def test_error_on_get_with_wrong_array_item_type_in_query(self):
    #     query_parameter = {
    #         "paramType": "query",
    #         "name": "test_param",
    #         "type": "array",
    #         "items": {"type": "integer"}
    #     }
    #     self.response["apis"][0]["operations"][0]["parameters"] = [
    #         query_parameter]
    #     self.register_urls()
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     self.assertRaises(TypeError, resource.testHTTP,
    #                       test_param=["NOT_INTEGER"])
    #
    # @httpretty.activate
    # def test_success_on_passing_datetime_in_param(self):
    #     query_parameter = {
    #         "paramType": "query",
    #         "name": "test_param",
    #         "type": "string",
    #         "format": "date-time"
    #     }
    #     self.response["apis"][0]["operations"][0]["parameters"] = [
    #         query_parameter]
    #     httpretty.register_uri(
    #         httpretty.GET, "http://localhost/test_http", body='')
    #     self.register_urls()
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     some_datetime = datetime.datetime(
    #         2014, 6, 10, 23, 49, 54, 728000, tzinfo=tzutc())
    #     resource.testHTTP(test_param=some_datetime).result()
    #     self.assertEqual(['2014-06-10 23:49:54.728000 00:00'],
    #                      httpretty.last_request().querystring['test_param'])
    #
    # @httpretty.activate
    # def test_success_on_passing_date_in_param(self):
    #     query_parameter = {
    #         "paramType": "query",
    #         "name": "test_param",
    #         "type": "string",
    #         "format": "date"
    #     }
    #     self.response["apis"][0]["operations"][0]["parameters"] = [
    #         query_parameter]
    #     httpretty.register_uri(
    #         httpretty.GET, "http://localhost/test_http", body='')
    #     self.register_urls()
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     some_date = datetime.date(2014, 6, 10)
    #     resource.testHTTP(test_param=some_date).result()
    #     self.assertEqual(['2014-06-10'],
    #                      httpretty.last_request().querystring['test_param'])
    #
    # @httpretty.activate
    # def test_success_on_post_with_path_query_and_body_params(self):
    #     query_parameter = self.parameter
    #     path_parameter = {
    #         "paramType": "path",
    #         "name": "param_id",
    #         "type": "string"
    #     }
    #     body_parameter = {
    #         "paramType": "body",
    #         "name": "body",
    #         "type": "string"
    #     }
    #     self.response["apis"][0]["path"] = "/params/{param_id}/test_http"
    #     operations = self.response["apis"][0]["operations"]
    #     operations[0]["method"] = "POST"
    #     operations[0]["parameters"] = [query_parameter,
    #                                    path_parameter,
    #                                    body_parameter]
    #     self.register_urls()
    #     httpretty.register_uri(
    #         httpretty.POST,
    #         "http://localhost/params/42/test_http?test_param=foo", body='')
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     resp = resource.testHTTP(test_param="foo", param_id="42",
    #                              body="some_test").result()
    #     self.assertEqual('some_test', httpretty.last_request().body)
    #     self.assertEqual(None, resp)
    #
    # @httpretty.activate
    # def test_success_on_post_with_array_in_body_params(self):
    #     body_parameter = {
    #         "paramType": "body",
    #         "name": "body",
    #         "type": "array",
    #         "items": {
    #             "type": "string"
    #         }
    #     }
    #     operations = self.response["apis"][0]["operations"]
    #     operations[0]["parameters"] = [body_parameter]
    #     operations[0]["method"] = "POST"
    #     self.register_urls()
    #     httpretty.register_uri(httpretty.POST, "http://localhost/test_http",
    #                            body='')
    #     resource = SwaggerClient.from_url(
    #         u'http://localhost/api-docs').api_test
    #     resp = resource.testHTTP(body=["a", "b", "c"]).result()
    #     self.assertEqual(["a", "b", "c"],
    #                      json.loads(httpretty.last_request().body))
    #     self.assertEqual(None, resp)
    #
    # # ToDo: Wrong body type not being checked as of now...
    # @httpretty.activate
    # def test_error_on_post_with_wrong_type_body(self):
    #     pytest.mark.xfail(reason='TODO')
    #
