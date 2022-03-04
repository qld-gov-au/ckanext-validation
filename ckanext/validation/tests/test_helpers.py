import datetime

from nose.tools import assert_equals, assert_in, with_setup

from ckan import model
from ckan.tests.helpers import reset_db
from ckan.tests import factories, helpers

from ckanext.validation.helpers import (
    get_validation_badge,
    validation_extract_report_from_errors,
)
from ckanext.validation.model import create_tables, tables_exist


def _test_org():
    org_name = 'test-org'

    def load_model_org():
        orgs = model.Session.query(model.Group)\
            .filter(model.Group.type == 'organization')\
            .filter(model.Group.name == org_name).all()
        if orgs:
            return orgs[0]

    org = load_model_org()
    if not org:
        factories.Organization(name=org_name)
        org = load_model_org()
    return org


def _assert_validation_status(resource, status):
    out = get_validation_badge(resource)

    assert 'href="/dataset/{}/resource/{}/validation"'.format(
        resource['package_id'], resource['id']) in out
    assert 'class="status {}"'.format(status) in out, "'{}' status not found in {}".format(status, out)


def _setup_function(self):
    reset_db()
    if not tables_exist():
        create_tables()
    self.owner_org = _test_org()
    self.test_dataset = factories.Dataset(owner_org=self.owner_org.id)


@with_setup(_setup_function)
class TestBadges(object):

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    def test_get_validation_badge_no_validation(self):

        resource = factories.Resource(
            format='CSV',
            package_id=self.test_dataset['id']
        )

        assert_equals(get_validation_badge(resource), '')

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    def test_get_validation_badge_success(self):

        resource = factories.Resource(
            format='CSV',
            package_id=self.test_dataset['id'],
            validation_status='success',
            validation_timestamp=datetime.datetime.utcnow().isoformat()
        )

        _assert_validation_status(resource, 'success')

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    def test_get_validation_badge_failure(self):

        resource = factories.Resource(
            format='CSV',
            package_id=self.test_dataset['id'],
            validation_status='failure',
            validation_timestamp=datetime.datetime.utcnow().isoformat()
        )

        _assert_validation_status(resource, 'invalid')

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    def test_get_validation_badge_error(self):

        resource = factories.Resource(
            format='CSV',
            package_id=self.test_dataset['id'],
            validation_status='error',
            validation_timestamp=datetime.datetime.utcnow().isoformat()
        )

        _assert_validation_status(resource, 'error')

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    def test_get_validation_badge_other(self):

        resource = factories.Resource(
            format='CSV',
            package_id=self.test_dataset['id'],
            validation_status='not-sure',
        )

        _assert_validation_status(resource, 'unknown')


class TestExtractReportFromErrors(object):

    def test_report_extracted(self):

        report = {
            'tables': [{'source': '/some/path'}],
            'error-count': 8
        }

        errors = {
            'some_field': ['Some error'],
            'validation': [report],
        }

        extracted_report, errors = validation_extract_report_from_errors(
            errors)

        assert_equals(extracted_report, report)
        assert_equals(errors['some_field'], ['Some error'])
        assert str(errors['validation'][0]).strip().startswith(
            'There are validation issues with this file')

        assert_in('data-module="modal-dialog"', str(errors['validation'][0]))

    def test_report_not_extracted(self):

        errors = {
            'some_field': ['Some error'],
            'some_other_field': ['Some other error']
        }

        report, errors = validation_extract_report_from_errors(errors)

        assert report is None
        assert_equals(errors['some_field'], ['Some error'])
        assert_equals(errors['some_other_field'], ['Some other error'])
