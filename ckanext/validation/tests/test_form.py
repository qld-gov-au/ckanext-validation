# encoding: utf-8

import datetime
import io
import json
import mock
import pytest
import unittest
from bs4 import BeautifulSoup
from six import ensure_binary

from ckantoolkit import check_ckan_version
from ckan.tests import helpers
from ckan.tests.factories import Sysadmin, Dataset, Organization
from ckan.tests.helpers import (
    FunctionalTestBase, call_action
)

from ckanext.validation.tests.helpers import (
    VALID_CSV, INVALID_CSV, mock_uploads, MockFieldStorage
)

if check_ckan_version('2.9'):
    NEW_RESOURCE_URL = '/dataset/{}/resource/new'
    EDIT_RESOURCE_URL = '/dataset/{}/resource/{}/edit'
else:
    NEW_RESOURCE_URL = '/dataset/new_resource/{}'
    EDIT_RESOURCE_URL = '/dataset/{}/resource_edit/{}'


def _get_resource_new_page_as_sysadmin(app, id):
    env = _get_extra_env_as_sysadmin()
    response = app.get(
        url=NEW_RESOURCE_URL.format(id),
        extra_environ=env,
    )
    return response


def _get_resource_update_page_as_sysadmin(app, id, resource_id):
    env = _get_extra_env_as_sysadmin()
    response = app.get(
        url=EDIT_RESOURCE_URL.format(id, resource_id),
        extra_environ=env,
    )
    return response


def _get_extra_env_as_sysadmin():
    user = Sysadmin()
    return {'REMOTE_USER': user['name'].encode('ascii')}


def _get_response_body(response):
    if hasattr(response, 'text'):
        return response.text
    else:
        return response.body


def _get_form(response):
    soup = BeautifulSoup(_get_response_body(response), 'html.parser')
    return soup.find('form', id='resource-edit')


def _post(app, url, data, resource_id='', upload=None):
    args = []
    env = _get_extra_env_as_sysadmin()
    # from the form
    data['id'] = resource_id
    data['save'] = ''

    if check_ckan_version('2.9'):
        if upload:
            for entry in upload:
                data[entry[0]] = (io.BytesIO(entry[2]), entry[1])
        kwargs = {
            'url': url,
            'data': data,
            'extra_environ': env
        }
    else:
        args.append(url)
        kwargs = {
            'params': data,
            'extra_environ': env,
            'upload_files': upload
        }

    return app.post(*args, **kwargs)


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceSchemaForm(object):

    def setup(self):
        self.app = helpers._get_test_app()

    def test_resource_form_includes_json_fields(self, app):
        dataset = Dataset()

        response = _get_resource_new_page_as_sysadmin(app, dataset['id'])
        form = _get_form(response)

        assert form.find("input", attrs={'name': 'schema'})
        assert form.find("textarea", attrs={'name': 'schema_json'})
        assert form.find("input", attrs={'name': 'schema_url'})

    def test_resource_form_create(self, app):
        dataset = Dataset()

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        json_value = json.dumps(value)

        params = {
            'name': 'test_resource_form_create',
            'package_id': dataset['id'],
            'url': 'https://example.com/data.csv',
            'schema': json_value,
        }

        _post(app, NEW_RESOURCE_URL.format(dataset['id']), params)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    def test_resource_form_create_json(self, app):
        dataset = Dataset()

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        json_value = json.dumps(value)

        params = {
            'name': 'test_resource_form_create_json',
            'package_id': dataset['id'],
            'url': 'https://example.com/data.csv',
            'schema_json': json_value,
        }

        _post(app, NEW_RESOURCE_URL.format(dataset['id']), params)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    @mock_uploads
    def test_resource_form_create_upload(self, mock_open):
        dataset = Dataset()
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        json_value = ensure_binary(json.dumps(value), encoding='utf-8')

        upload = ('schema_upload', 'schema.json', json_value)
        params = {
            'name': 'test_resource_form_create_upload',
            'url': 'https://example.com/data.csv',
        }

        _post(self.app, NEW_RESOURCE_URL.format(dataset['id']),
              params, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    def test_resource_form_create_url(self, app):
        dataset = Dataset()

        value = 'https://example.com/schemas.json'

        params = {
            'name': 'test_resource_form_create_url',
            'package_id': dataset['id'],
            'url': 'https://example.com/data.csv',
            'schema_json': value,
        }

        _post(app, NEW_RESOURCE_URL.format(dataset['id']), params)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    def test_resource_form_update(self, app):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = Dataset(
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )

        resource_id = dataset['resources'][0]['id']

        response = _get_resource_update_page_as_sysadmin(
            app, dataset['id'], resource_id)
        form = _get_form(response)

        assert form.find(attrs={'name': "schema"})['value'] == \
            json.dumps(value, indent=None)

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'},
                {'name': 'date'}
            ]
        }

        json_value = json.dumps(value)

        params = {
            'name': 'test_resource_form_update',
            'url': 'https://example.com/data.csv',
            'schema': json_value
        }

        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
              params, resource_id=resource_id)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    def test_resource_form_update_json(self, app):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = Dataset(
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )

        resource_id = dataset['resources'][0]['id']

        response = _get_resource_update_page_as_sysadmin(
            app, dataset['id'], resource_id)
        form = _get_form(response)

        assert form.find(attrs={'name': "schema_json"}).text == \
            json.dumps(value, indent=2)

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'},
                {'name': 'date'}
            ]
        }

        json_value = json.dumps(value)

        params = {
            'name': 'test_resource_form_update_json',
            'url': 'https://example.com/data.csv',
            'schema_json': json_value
        }

        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
              params, resource_id=resource_id)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    def test_resource_form_update_url(self, app):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = Dataset(
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        response = _get_resource_update_page_as_sysadmin(
            app, dataset['id'], resource_id)
        form = _get_form(response)

        assert form.find(attrs={'name': "schema_json"}).text ==\
            json.dumps(value, indent=2)

        value = 'https://example.com/schema.json'

        params = {
            'name': 'test_resource_form_update_url',
            'url': 'https://example.com/data.csv',
            'schema_url': value
        }

        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
              params, resource_id=resource_id)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value

    def test_resource_form_update_upload(self, app):
        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'}
            ]
        }
        dataset = Dataset(
            resources=[{
                'url': 'https://example.com/data.csv',
                'schema': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        response = _get_resource_update_page_as_sysadmin(
            app, dataset['id'], resource_id)
        form = _get_form(response)

        assert form.find(attrs={'name': "schema_json"}).text == \
            json.dumps(value, indent=2)

        value = {
            'fields': [
                {'name': 'code'},
                {'name': 'department'},
                {'name': 'date'}
            ]
        }

        json_value = ensure_binary(json.dumps(value), encoding='utf-8')

        upload = ('schema_upload', 'schema.json', json_value)
        params = {
            'name': 'test_resource_form_update_upload',
            'url': 'https://example.com/data.csv',
        }

        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
              params, resource_id=resource_id, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['schema'] == value


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOptionsForm(object):

    def test_resource_form_includes_json_fields(self, app):
        dataset = Dataset()

        response = _get_resource_new_page_as_sysadmin(app, dataset['id'])
        form = _get_form(response)

        assert form.find("textarea", attrs={'name': 'validation_options'})

    def test_resource_form_create(self, app):
        dataset = Dataset()

        value = {
            'delimiter': ';',
            'headers': 2,
            'skip_rows': ['#'],
        }
        json_value = json.dumps(value)
        params = {
            'name': 'test_resource_form_create',
            'url': 'https://example.com/data.csv',
            'validation_options': json_value,
        }

        _post(app, NEW_RESOURCE_URL.format(dataset['id']), params)

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['validation_options'] == value

    def test_resource_form_update(self, app):
        value = {
            'delimiter': ';',
            'headers': 2,
            'skip_rows': ['#'],
        }

        dataset = Dataset(
            resources=[{
                'url': 'https://example.com/data.csv',
                'validation_options': value
            }]
        )
        resource_id = dataset['resources'][0]['id']

        response = _get_resource_update_page_as_sysadmin(
            app, dataset['id'], resource_id)
        form = _get_form(response)

        assert form.find("textarea",
                         attrs={'name': 'validation_options'}).text ==\
            json.dumps(value, indent=2, sort_keys=True)

        value = {
            'delimiter': ';',
            'headers': 2,
            'skip_rows': ['#'],
            'skip_tests': ['blank-rows'],
        }

        json_value = json.dumps(value)

        params = {
            'name': 'test_resource_form_update',
            'url': 'https://example.com/data.csv',
            'validation_options': json_value
        }

        _post(app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
              params, resource_id=resource_id)
        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['validation_options'] == value


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOnCreateForm(FunctionalTestBase):

    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg['ckanext.validation.run_on_create_sync'] = True

    def setup(self):
        self.app = helpers._get_test_app()

    @mock_uploads
    def test_resource_form_create_valid(self, mock_open):
        dataset = Dataset()

        upload = ('upload', 'valid.csv', VALID_CSV)

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        params = {
            'name': 'test_resource_form_create_valid',
            'url': 'https://example.com/data.csv'
        }

        with mock.patch('io.open', return_value=valid_stream):
            _post(self.app, NEW_RESOURCE_URL.format(dataset['id']),
                  params, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['validation_status'] == 'success'
        assert 'validation_timestamp' in dataset['resources'][0]

    @unittest.skip("TODO Fix file mocks so this can run")
    @pytest.mark.ckan_config('ckanext.validation.run_on_create_sync', True)
    @pytest.mark.ckan_config('ckanext.validation.run_on_update_sync', True)
    @mock_uploads
    def test_resource_form_create_invalid(self, mock_open):
        user = Sysadmin()
        org = Organization(user=user)
        dataset = Dataset(owner_org=org['id'])

        upload = ('upload', 'invalid.csv', INVALID_CSV)

        invalid_stream = io.BufferedReader(io.BytesIO(INVALID_CSV))

        params = {
            'name': 'test_resource_form_create_invalid',
            'url': 'https://example.com/data.csv'
        }

        with mock.patch('io.open', return_value=invalid_stream):
            response = _get_response_body(_post(self.app, NEW_RESOURCE_URL.format(dataset['id']),
                                          params, upload=[upload]))
        print(response)
        dataset = call_action('package_show', id=dataset['id'])
        print(dataset)

        assert 'validation' in response
        assert 'missing-value' in response
        assert 'Row 2 has a missing value in column 4' in response


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOnUpdateForm(FunctionalTestBase):

    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg['ckanext.validation.run_on_update_sync'] = True

    def setup(self):
        self.app = helpers._get_test_app()

    @mock_uploads
    def test_resource_form_update_valid(self, mock_open):
        dataset = Dataset(resources=[
            {
                'url': 'https://example.com/data.csv'
            }
        ])

        upload = ('upload', 'valid.csv', VALID_CSV)

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        params = {
            'name': 'test_resource_form_update_valid',
            'url': 'https://example.com/data.csv'
        }
        resource_id = dataset['resources'][0]['id']

        with mock.patch('io.open', return_value=valid_stream):
            _post(self.app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
                  params, resource_id=resource_id, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['validation_status'] == 'success'
        assert 'validation_timestamp' in dataset['resources'][0]

    @unittest.skip("TODO Fix file mocks so this can run")
    @mock_uploads
    def test_resource_form_update_invalid(self, mock_open):

        dataset = Dataset(
            resources=[{
                'name': 'test_resource_form_update_invalid',
                'url': 'https://example.com/data.csv'
            }]
        )
        resource_id = dataset['resources'][0]['id']

        response = _get_resource_update_page_as_sysadmin(
            self.app, dataset['id'], resource_id)

        upload = ('upload', 'invalid.csv', INVALID_CSV)
        params = {}

        invalid_stream = io.BufferedReader(io.BytesIO(INVALID_CSV))

        with mock.patch('io.open', return_value=invalid_stream):
            response = _get_response_body(_post(
                self.app, EDIT_RESOURCE_URL.format(dataset['id'], resource_id),
                params, resource_id=resource_id, upload=[upload]))
            print(response)
        print(dir(response))
        assert 'validation' in response
        assert 'missing-value' in response
        assert 'Row 2 has a missing value in column 4' in response


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationFieldsPersisted(FunctionalTestBase):

    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg['ckanext.validation.run_on_create_sync'] = True
        cfg['ckanext.validation.run_on_update_sync'] = True

    def setup(self):
        self.app = helpers._get_test_app()
        pass

    @mock_uploads
    def test_resource_form_fields_are_persisted(self, mock_open):
        upload = ('upload', 'valid.csv', VALID_CSV)
        upload_file = MockFieldStorage(io.BytesIO(VALID_CSV), filename='data.csv')

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        dataset = Dataset()
        with mock.patch('io.open', return_value=valid_stream):
            resource = call_action(
                'resource_create',
                package_id=dataset['id'],
                validation_status='success',
                validation_timestamp=datetime.datetime.now().isoformat(),
                upload=upload_file,
                url='data.csv')
        resource = call_action('resource_show', id=resource['id'])
        assert 'validation_status' in resource
        assert resource['validation_status'] == 'success'
        assert not resource.get('description')
        resource_id = resource['id']

        params = {
            'description': 'test desc'
        }

        dataset = call_action('package_show', id=dataset['id'])

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        with mock.patch('io.open', return_value=valid_stream):
            _post(self.app, EDIT_RESOURCE_URL.format(dataset['id'], resource['id']),
                  params, resource_id=resource_id, upload=[upload])

        dataset = call_action('package_show', id=dataset['id'])

        assert dataset['resources'][0]['validation_status'] == 'success'
        assert 'validation_timestamp' in dataset['resources'][0]
        assert dataset['resources'][0]['description'] == 'test desc'
