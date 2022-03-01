# encoding: utf-8

import datetime
import json
import io
import mock
import six

from bs4 import BeautifulSoup
from nose.tools import assert_in, assert_equals, with_setup

from ckantoolkit import check_ckan_version
from ckantoolkit.tests import factories, helpers
from ckantoolkit.tests.helpers import call_action, reset_db

from ckanext.validation.model import create_tables, tables_exist
from ckanext.validation.tests.helpers import (
    VALID_CSV, INVALID_CSV, mock_uploads, MockFieldStorage
)

if check_ckan_version('2.9'):
    NEW_RESOURCE_URL = '/dataset/{}/resource/new'
    EDIT_RESOURCE_URL = '/dataset/{}/resource/{}/edit'
else:
    NEW_RESOURCE_URL = '/dataset/new_resource/{}'
    EDIT_RESOURCE_URL = '/dataset/{}/resource_edit/{}'


def _post(app, url, data, upload=None):
    args = []
    if check_ckan_version('2.9'):
        user = factories.Sysadmin()
        if upload:
            for entry in upload:
                data[entry[0]] = (six.StringIO(entry[2]), entry[1])
        kwargs = {
            'url': url,
            'data': data,
            'extra_environ': {'REMOTE_USER': user['name'].encode('ascii')}
        }
    else:
        admin_pass = "RandomPassword123"
        sysadmin = factories.Sysadmin(password=admin_pass)
        app.post("/login_generic?came_from=/user/logged_in", params={
            "save": "",
            "login": sysadmin["name"],
            "password": admin_pass,
        })

        args.append(url)
        kwargs = {
            'params': data,
            'upload_files': upload
        }
    return app.post(*args, **kwargs)


def _get_resource_new_page_as_sysadmin(app, id):
    user = factories.Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/dataset/new_resource/{}'.format(id),
        extra_environ=env,
    )
    return env, response


def _get_response_body(response):
    if hasattr(response, 'text'):
        return response.text
    else:
        return response.body


def _setup_function(self):
    reset_db()
    if not tables_exist():
        create_tables()
    self.owner_org = factories.Organization(name='test-org')


@with_setup(_setup_function)
class TestResourceSchemaForm(object):

    def test_resource_form_includes_json_fields(self):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        app = helpers._get_test_app()
        env, response = _get_resource_new_page_as_sysadmin(app, dataset['id'])
        soup = BeautifulSoup(_get_response_body(response), 'html.parser')

        assert soup.select("#resource-edit input[name='schema']")
        assert soup.select("#resource-edit input[name='schema_url']")
        assert soup.select("#resource-edit textarea[name='schema_json']")

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    def test_resource_form_create(self):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create',
            'url': 'https://example.com/data.csv',
            'schema': json_value
        }

        app = helpers._get_test_app()
        _post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    def test_resource_form_create_json(self):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create_json',
            'url': 'https://example.com/data.csv',
            'schema_json': json_value
        }

        app = helpers._get_test_app()
        _post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @mock_uploads
    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    def test_resource_form_create_upload(self, mock_open):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create_upload',
            'url': 'https://example.com/data.csv'
        }
        upload = ('schema_upload', 'schema.json', json_value)

        app = helpers._get_test_app()
        _post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    def test_resource_form_create_url(self):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        value = 'https://example.com/schemas.json'

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create_url',
            'url': 'https://example.com/data.csv',
            'schema_json': value
        }

        app = helpers._get_test_app()
        _post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    @helpers.change_config('ckanext.validation.run_on_update_async', False)
    def test_resource_form_update(self):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'},
                {'name': 'date'}
            ]
        }

        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': resource_id,
            'name': 'test_resource_form_update',
            'url': 'https://example.com/data.csv',
            'schema': json_value,
            'schema_json': ''
        }

        app = helpers._get_test_app()
        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    @helpers.change_config('ckanext.validation.run_on_update_async', False)
    def test_resource_form_update_json(self):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'},
                {'name': 'date'}
            ]
        }

        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': resource_id,
            'name': 'test_resource_form_update_json',
            'url': 'https://example.com/data.csv',
            'schema_json': json_value
        }

        app = helpers._get_test_app()
        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    @helpers.change_config('ckanext.validation.run_on_update_async', False)
    def test_resource_form_update_url(self):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        value = 'https://example.com/schema.json'

        post_data = {
            'save': '',
            'id': resource_id,
            'name': 'test_resource_form_update_url',
            'url': 'https://example.com/data.csv',
            'schema_url': value
        }

        app = helpers._get_test_app()
        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)

    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    @helpers.change_config('ckanext.validation.run_on_update_async', False)
    def test_resource_form_update_upload(self):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'},
                {'name': 'date'}
            ]
        }

        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': resource_id,
            'name': 'test_resource_form_update_upload',
            'url': 'https://example.com/data.csv'
        }
        upload = ('schema_upload', 'schema.json', json_value)

        app = helpers._get_test_app()
        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id), post_data, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['schema'], value)


@with_setup(_setup_function)
class TestResourceValidationOptionsForm(object):

    def test_resource_form_includes_json_fields(self):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        app = helpers._get_test_app()
        env, response = _get_resource_new_page_as_sysadmin(app, dataset['id'])
        soup = BeautifulSoup(_get_response_body(response), 'html.parser')

        assert soup.select("#resource-edit textarea[name='validation_options']")

    def test_resource_form_create(self):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        value = {
            'delimiter': ';',
            'headers': 2,
            'skip_rows': ['#'],
        }
        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create',
            'url': 'https://example.com/data.csv',
            'validation_options': json_value
        }

        app = helpers._get_test_app()
        _post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['validation_options'], value)

    def test_resource_form_update(self):
        value = {
            'delimiter': ';',
            'headers': 2,
            'skip_rows': ['#'],
        }

        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'url': 'https://example.com/data.csv',
                'validation_options': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        value = {
            'delimiter': ';',
            'headers': 2,
            'skip_rows': ['#'],
            'skip_tests': ['blank-rows'],
        }

        json_value = json.dumps(value)

        post_data = {
            'save': '',
            'id': resource_id,
            'name': 'test_resource_form_update',
            'url': 'https://example.com/data.csv',
            'validation_options': json_value
        }

        app = helpers._get_test_app()
        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id), post_data)

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['validation_options'], value)


@with_setup(_setup_function)
class TestResourceValidationOnCreateForm(object):

    @mock_uploads
    @helpers.change_config('ckanext.validation.run_on_create_sync', True)
    @helpers.change_config('ckanext.validation.run_on_update_sync', True)
    def test_resource_form_create_valid(self, mock_open):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create_valid',
            'url': 'https://example.com/data.csv'
        }

        upload = ('upload', 'valid.csv', VALID_CSV)

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        app = helpers._get_test_app()
        with mock.patch('io.open', return_value=valid_stream):
            _post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['validation_status'], 'success')
        assert 'validation_timestamp' in dataset['resources'][0]

    @mock_uploads
    @helpers.change_config('ckanext.validation.run_on_create_sync', True)
    @helpers.change_config('ckanext.validation.run_on_update_sync', True)
    def test_resource_form_create_invalid(self, mock_open):
        dataset = factories.Dataset(owner_org=self.owner_org['id'])

        post_data = {
            'save': '',
            'id': '',
            'name': 'test_resource_form_create_invalid',
            'url': 'https://example.com/data.csv'
        }

        upload = ('upload', 'invalid.csv', INVALID_CSV)

        invalid_stream = io.BufferedReader(io.BytesIO(INVALID_CSV))

        app = helpers._get_test_app()
        with mock.patch('io.open', return_value=invalid_stream):
            response = _get_response_body(_post(app, NEW_RESOURCE_URL.format(dataset['id']), post_data, upload=[upload]))

        assert_in('validation', response)
        assert_in('missing-value', response)
        assert_in('Row 2 has a missing value in column 4', response)


@with_setup(_setup_function)
class TestResourceValidationOnUpdateForm(object):

    @mock_uploads
    @helpers.change_config('ckanext.validation.run_on_update_sync', True)
    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    def test_resource_form_update_valid(self, mock_open):

        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'url': 'https://example.com/data.csv'
            }]
        )
        resource_id = dataset['resources'][0]['id']

        post_data = {
            'save': '',
            'id': resource_id,
            'name': 'test_resource_form_update_valid',
            'url': 'https://example.com/data.csv'
        }
        upload = ('upload', 'valid.csv', VALID_CSV)

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        app = helpers._get_test_app()
        with mock.patch('io.open', return_value=valid_stream):
            _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id), post_data, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['validation_status'], 'success')
        assert 'validation_timestamp' in dataset['resources'][0]

    @mock_uploads
    @helpers.change_config('ckanext.validation.run_on_create_async', False)
    @helpers.change_config('ckanext.validation.run_on_update_sync', True)
    def test_resource_form_update_invalid(self, mock_open):

        dataset = factories.Dataset(
            owner_org=self.owner_org['id'],
            resources=[{
                'name': 'test_resource_form_update_invalid',
                'url': 'https://example.com/data.csv'
            }]
        )
        resource = dataset['resources'][0]

        app = helpers._get_test_app()
        response = app.get("/dataset/{}/resource/{}".format(dataset['id'], resource['id']))
        soup = BeautifulSoup(_get_response_body(response), 'html.parser')
        assert soup.select("h1.page-heading") and soup.select("h1.page-heading")[0].string.strip() == resource['name']

        post_data = {
            'save': '',
            'id': resource['id'],
            'name': 'test_resource_form_update_invalid',
            'url': 'https://example.com/data.csv'
        }
        upload = ('upload', 'invalid.csv', INVALID_CSV)

        invalid_stream = io.BufferedReader(io.BytesIO(INVALID_CSV))

        with mock.patch('io.open', return_value=invalid_stream):
            response = _get_response_body(_post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource['id']), post_data, upload=[upload]))

        assert_in('validation', response)
        assert_in('missing-value', response)
        assert_in('Row 2 has a missing value in column 4', response)


@with_setup(_setup_function)
class TestResourceValidationFieldsPersisted(object):

    @helpers.change_config('ckanext.validation.run_on_create_sync', True)
    @helpers.change_config('ckanext.validation.run_on_update_sync', True)
    def test_resource_form_fields_are_persisted(self):
        upload = ('upload', 'valid.csv', VALID_CSV)

        dataset = factories.Dataset(owner_org=self.owner_org['id'])
        resource = call_action(
            'resource_create',
            package_id=dataset['id'],
            validation_status='success',
            validation_timestamp=datetime.datetime.now().isoformat(),
            upload=MockFieldStorage(io.BytesIO(VALID_CSV), filename='data.csv'),
            url='data.csv')
        resource = call_action('resource_show', id=resource['id'])
        assert 'validation_status' in resource
        assert resource['validation_status'] == 'success'

        post_data = {
            'save': '',
            'id': resource['id'],
            'name': 'test_resource_form_fields_are_persisted',
            'description': 'test desc',
            'url': 'https://example.com/data.csv'
        }

        app = helpers._get_test_app()
        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource['id']), post_data, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['validation_status'], 'success')
        assert 'validation_timestamp' in dataset['resources'][0]
        assert_equals(dataset['resources'][0]['description'], 'test desc')
