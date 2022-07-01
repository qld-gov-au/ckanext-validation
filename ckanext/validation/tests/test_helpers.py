import datetime

import pytest

from ckan.tests import factories

from ckanext.validation.helpers import (
    get_validation_badge,
    validation_extract_report_from_errors,
)


def _assert_validation_badge_status(resource, status):
    out = get_validation_badge(resource)

    assert 'href="/dataset/{}/resource/{}/validation"'.format(
        resource['package_id'], resource['id']) in out
    assert 'class="status {}"'.format(status) in out


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestBadges(object):

    def test_get_validation_badge_no_validation(self):

        resource = factories.Resource(
            format='CSV',
        )

        assert get_validation_badge(resource) == ''

    def test_get_validation_badge_success(self):

        resource = factories.Resource(
            format='CSV',
            validation_status='success',
            validation_timestamp=datetime.datetime.utcnow().isoformat()
        )

        _assert_validation_badge_status(resource, 'success')

    def test_get_validation_badge_failure(self):

        resource = factories.Resource(
            format='CSV',
            validation_status='failure',
            validation_timestamp=datetime.datetime.utcnow().isoformat()
        )

        _assert_validation_badge_status(resource, 'invalid')

    def test_get_validation_badge_error(self):

        resource = factories.Resource(
            format='CSV',
            validation_status='error',
            validation_timestamp=datetime.datetime.utcnow().isoformat()
        )

        _assert_validation_badge_status(resource, 'error')

    def test_get_validation_badge_other(self):

        resource = factories.Resource(
            format='CSV',
            validation_status='not-sure',
        )

        _assert_validation_badge_status(resource, 'unknown')


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

        assert extracted_report == report
        assert errors['some_field'] == ['Some error']
        assert str(errors['validation'][0]).strip().startswith(
            'There are validation issues with this file')

        assert 'data-module="modal-dialog"' in str(errors['validation'][0])

    def test_report_not_extracted(self):

        errors = {
          'some_field': ['Some error'],
          'some_other_field': ['Some other error']
        }

        report, errors = validation_extract_report_from_errors(errors)

        assert report is None
        assert errors['some_field'] == ['Some error']
        assert errors['some_other_field'] == ['Some other error']
