# encoding: utf-8

import io
import json

import responses
import mock
import pytest

import ckantoolkit
from ckan.lib.uploader import ResourceUpload
from ckan.tests.helpers import call_action
from ckan.tests import factories

import ckanext.validation.settings as s
from ckanext.validation.model import Validation
from ckanext.validation.jobs import (run_validation_job, uploader, Session,
                                     requests)
from ckanext.validation.tests.helpers import (INVALID_REPORT, VALID_REPORT, ERROR_REPORT,
                                              VALID_REPORT_LOCAL_FILE,
                                              VALID_CSV, INVALID_CSV, SCHEMA,
                                              MockFieldStorage,
                                              MOCK_ASYNC_VALIDATE)


class MockUploader(ResourceUpload):

    def get_path(self, resource_id):
        return '/tmp/example/{}'.format(resource_id)


def mock_get_resource_uploader(data_dict):
    return MockUploader(data_dict)


@pytest.mark.usefixtures("clean_db", "validation_setup")
@pytest.mark.ckan_config(s.UPDATE_MODE, s.ASYNC_MODE)
@pytest.mark.ckan_config(s.CREATE_MODE, s.ASYNC_MODE)
class TestValidationJob(object):

    @mock.patch(MOCK_ASYNC_VALIDATE, return_value=VALID_REPORT)
    @mock.patch.object(Session, 'commit')
    @mock.patch.object(ckantoolkit, 'get_action')
    @mock.patch.object(requests, 'Session', return_value='Some_Session')
    def test_job_run_no_schema(self, mock_requests, mock_get_action,
                               mock_commit, mock_validate, dataset):
        resource = {
            'id': 'test',
            'url': 'http://example.com/file.csv',
            'format': 'csv',
            'package_id': dataset['id'],
        }

        run_validation_job(resource)

        mock_validate.assert_called_with('http://example.com/file.csv',
                                         format='csv',
                                         http_session='Some_Session',
                                         schema=None)

    @mock.patch(MOCK_ASYNC_VALIDATE, return_value=VALID_REPORT)
    @mock.patch.object(Session, 'commit')
    @mock.patch.object(ckantoolkit, 'get_action')
    @mock.patch.object(requests, 'Session', return_value='Some_Session')
    def test_job_run_schema(self, mock_requests, mock_get_action, mock_commit,
                            mock_validate, dataset):
        resource = {
            'id': 'test',
            'url': 'http://example.com/file.csv',
            'format': 'csv',
            'schema': json.dumps(SCHEMA),
            'package_id': dataset['id'],
        }

        run_validation_job(resource)

        mock_validate.assert_called_with('http://example.com/file.csv',
                                         format='csv',
                                         http_session='Some_Session',
                                         schema=SCHEMA)

    @mock.patch(MOCK_ASYNC_VALIDATE, return_value=VALID_REPORT)
    @mock.patch.object(uploader,
                       'get_resource_uploader',
                       return_value=mock_get_resource_uploader({}))
    @mock.patch.object(Session, 'commit')
    @mock.patch.object(ckantoolkit, 'get_action')
    @mock.patch.object(requests, 'Session', return_value='Some_Session')
    def test_job_run_uploaded_file(self, mock_requests, mock_get_action,
                                   mock_commit, mock_uploader, mock_validate,
                                   dataset):
        resource = {
            'id': 'test',
            'url': '__upload',
            'url_type': 'upload',
            'format': 'csv',
            'package_id': dataset['id'],
        }

        run_validation_job(resource)

        mock_validate.assert_called_with('/tmp/example/{}'.format(
            resource['id']),
                                         format='csv',
                                         http_session='Some_Session',
                                         schema=None)

    def test_job_run_valid_stores_validation_object(self, mocked_responses):
        url = 'http://example.com/file.csv'

        mocked_responses.add(responses.GET, url, body=VALID_CSV)
        resource = factories.Resource(url=url, format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.status == 'success'
        assert validation.report['error-count'] == 0
        assert validation.report['table-count'] == 1
        assert validation.report['tables'][0]['source'] == url
        assert validation.finished

    @mock.patch(MOCK_ASYNC_VALIDATE, return_value=INVALID_REPORT)
    def test_job_run_invalid_stores_validation_object(self, mock_report, resource_factory):
        url = "http://example.com/invalid.csv"
        resource = resource_factory(do_not_validate=True, url=url)

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.status == 'failure'
        assert validation.report['error-count'] == 2
        assert validation.report['table-count'] == 1
        assert validation.report['tables'][0]['source'] == url
        assert validation.finished

    @mock.patch(MOCK_ASYNC_VALIDATE, return_value=ERROR_REPORT)
    def test_job_run_error_stores_validation_object(self, mock_validate):
        resource = factories.Resource(url='http://example.com/file.csv',
                                      format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.status == 'error'
        assert validation.report is None
        assert validation.error == {'message': 'Some warning'}
        assert validation.finished

    def test_job_run_uploaded_file_replaces_paths(self, resource_factory):

        resource = resource_factory()

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.report['tables'][0]['source'].startswith('http')

    def test_job_run_valid_stores_status_in_resource(self, resource_factory):
        resource = resource_factory(do_not_validate=True)
        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        res = call_action('resource_show', id=resource['id'])

        assert res['validation_status'] == validation.status
        assert res['validation_timestamp'] == validation.finished.isoformat()

    def test_job_local_paths_are_hidden(self, resource_factory):
        """Local path for a resource file must be hidden inside report"""
        upload = MockFieldStorage(io.BytesIO(INVALID_CSV), 'invalid.csv')
        resource = resource_factory(upload=upload, do_not_validate=True)

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        source = validation.report['tables'][0]['source']
        assert source.startswith('http')
        assert source.endswith('invalid.csv')

    def test_job_pass_validation_options(self, resource_factory):
        valid_csv = b'a,b,c,d\n#comment\n1,2,3,4'
        upload = MockFieldStorage(io.BytesIO(valid_csv), 'valid.csv')

        validation_options = {'headers': 1, 'skip_rows': ['#']}

        resource = resource_factory(upload=upload,
                                    validation_options=validation_options,
                                    do_not_validate=True)

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.report['valid']

    def test_job_pass_validation_options_string(self, resource_factory):
        invalid_csv = b'a;b;c;d\n#comment\n1;2;3;4'

        validation_options = '''{
            "headers": 1,
            "skip_rows": ["#"],
            "delimiter": ";"
        }'''

        mock_upload = MockFieldStorage(io.BytesIO(invalid_csv), 'invalid.csv')

        resource = resource_factory(upload=mock_upload,
                                    validation_options=validation_options,
                                    do_not_validate=True)

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.report['valid']
