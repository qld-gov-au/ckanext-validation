import mock
import json
import io

import pytest
from six import BytesIO

import ckantoolkit
from ckan.lib.uploader import ResourceUpload
from ckan.tests.helpers import call_action, change_config
from ckan.tests import factories

from ckanext.validation.model import Validation
from ckanext.validation.jobs import (
    run_validation_job, uploader, Session, requests)
from ckanext.validation.tests.helpers import (
        VALID_REPORT, INVALID_REPORT, ERROR_REPORT, VALID_REPORT_LOCAL_FILE,
        mock_uploads, MockFieldStorage
)


class MockUploader(ResourceUpload):

    def get_path(self, resource_id):
        return '/tmp/example/{}'.format(resource_id)


def mock_get_resource_uploader(data_dict):
    return MockUploader(data_dict)


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestValidationJob(object):

    @change_config('ckanext.validation.run_on_create_async', False)
    @mock.patch('ckanext.validation.jobs.validate', return_value=VALID_REPORT)
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
        print("HERE-2")
        run_validation_job(resource)

        mock_validate.assert_called_with(
            'http://example.com/file.csv',
            format='csv',
            http_session='Some_Session',
            schema=None)

    @mock.patch('ckanext.validation.jobs.validate', return_value=VALID_REPORT)
    @mock.patch.object(Session, 'commit')
    @mock.patch.object(ckantoolkit, 'get_action')
    @mock.patch.object(requests, 'Session', return_value='Some_Session')
    def test_job_run_schema(
         self, mock_requests, mock_get_action,
         mock_commit, mock_validate, dataset):

        schema = {
            'fields': [
                {'name': 'id', 'type': 'integer'},
                {'name': 'description', 'type': 'string'}
            ]
        }
        resource = {
            'id': 'test',
            'url': 'http://example.com/file.csv',
            'format': 'csv',
            'schema': json.dumps(schema),
            'package_id': dataset['id'],
        }

        run_validation_job(resource)

        mock_validate.assert_called_with(
            'http://example.com/file.csv',
            format='csv',
            http_session='Some_Session',
            schema=schema)

    @mock.patch('ckanext.validation.jobs.validate', return_value=VALID_REPORT)
    @mock.patch.object(uploader, 'get_resource_uploader',
                       return_value=mock_get_resource_uploader({}))
    @mock.patch.object(Session, 'commit')
    @mock.patch.object(ckantoolkit, 'get_action')
    @mock.patch.object(requests, 'Session', return_value='Some_Session')
    def test_job_run_uploaded_file(self, mock_requests,
                                   mock_get_action, mock_commit,
                                   mock_uploader, mock_validate, dataset):

        resource = {
            'id': 'test',
            'url': '__upload',
            'url_type': 'upload',
            'format': 'csv',
            'package_id': dataset['id'],
        }

        run_validation_job(resource)

        mock_validate.assert_called_with(
            '/tmp/example/{}'.format(resource['id']),
            format='csv',
            http_session='Some_Session',
            schema=None)

    @mock.patch('ckanext.validation.jobs.validate',
                return_value=VALID_REPORT)
    def test_job_run_valid_stores_validation_object(self, mock_validate):

        resource = factories.Resource(
            url='http://example.com/file.csv', format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.status == 'success'
        assert validation.report == VALID_REPORT
        assert validation.finished

    @mock.patch('ckanext.validation.jobs.validate',
                return_value=INVALID_REPORT)
    def test_job_run_invalid_stores_validation_object(self, mock_validate):

        resource = factories.Resource(
            url='http://example.com/file.csv', format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.status == 'failure'
        assert validation.report == INVALID_REPORT
        assert validation.finished

    @mock.patch('ckanext.validation.jobs.validate',
                return_value=ERROR_REPORT)
    def test_job_run_error_stores_validation_object(self, mock_validate):

        resource = factories.Resource(
            url='http://example.com/file.csv', format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.status == 'error'
        assert validation.report is None
        assert validation.error == {'message': 'Some warning'}
        assert validation.finished

    @mock.patch('ckanext.validation.jobs.validate',
                return_value=VALID_REPORT_LOCAL_FILE)
    @mock.patch.object(uploader, 'get_resource_uploader',
                       return_value=mock_get_resource_uploader({}))
    def test_job_run_uploaded_file_replaces_paths(
            self, mock_uploader, mock_validate):

        resource = factories.Resource(
                url='__upload', url_type='upload', format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.report['tables'][0]['source'].startswith('http')

    @mock.patch('ckanext.validation.jobs.validate',
                return_value=VALID_REPORT)
    def test_job_run_valid_stores_status_in_resource(self, mock_validate):

        resource = factories.Resource(
            url='http://example.com/file.csv', format='csv')

        run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        updated_resource = call_action('resource_show', id=resource['id'])

        assert updated_resource['validation_status'] == validation.status
        assert updated_resource['validation_timestamp'] ==\
               validation.finished.isoformat()

    @mock_uploads
    def test_job_local_paths_are_hidden(self, mock_open):

        invalid_csv = bytes('id,type\n' + '1,a,\n' * 1010, encoding='utf-8')
        invalid_file = BytesIO()

        invalid_file.write(invalid_csv)

        mock_upload = MockFieldStorage(invalid_file, 'invalid.csv')

        resource = factories.Resource(format='csv', upload=mock_upload)

        invalid_stream = io.BufferedReader(io.BytesIO(invalid_csv))

        with mock.patch('io.open', return_value=invalid_stream):

            run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        source = validation.report['tables'][0]['source']
        assert source.startswith('http')
        assert source.endswith('invalid.csv')

        warning = validation.report['warnings'][0]
        assert warning == 'Table inspection has reached 1000 row(s) limit'

    @mock_uploads
    def test_job_pass_validation_options(self, mock_open):

        invalid_csv = b'''

a,b,c
#comment
1,2,3
'''

        validation_options = {
            'headers': 3,
            'skip_rows': ['#']
        }

        invalid_file = BytesIO()

        invalid_file.write(invalid_csv)

        mock_upload = MockFieldStorage(invalid_file, 'invalid.csv')

        resource = factories.Resource(
            format='csv',
            upload=mock_upload,
            validation_options=validation_options)

        invalid_stream = io.BufferedReader(BytesIO(invalid_csv))

        with mock.patch('io.open', return_value=invalid_stream):

            run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.report['valid']

    @mock_uploads
    def test_job_pass_validation_options_string(self, mock_open):

        invalid_csv = b'''

a;b;c
#comment
1;2;3
'''

        validation_options = '''{
            "headers": 3,
            "skip_rows": ["#"]
        }'''

        invalid_file = BytesIO()

        invalid_file.write(invalid_csv)

        mock_upload = MockFieldStorage(invalid_file, 'invalid.csv')

        resource = factories.Resource(
            format='csv',
            upload=mock_upload,
            validation_options=validation_options)

        invalid_stream = io.BufferedReader(BytesIO(invalid_csv))

        with mock.patch('io.open', return_value=invalid_stream):

            run_validation_job(resource)

        validation = Session.query(Validation).filter(
            Validation.resource_id == resource['id']).one()

        assert validation.report['valid']
