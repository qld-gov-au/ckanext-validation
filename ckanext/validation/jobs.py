# encoding: utf-8

import logging
import json
import re
import six

import requests
from goodtables import validate

from ckan.model import Session
import ckan.lib.uploader as uploader

import ckantoolkit as t

from ckanext.validation.validation_status_helper import (ValidationStatusHelper, ValidationJobDoesNotExist,
                                                         ValidationJobAlreadyRunning, StatusTypes)

log = logging.getLogger(__name__)


def run_validation_job(resource=None):
    vsh = ValidationStatusHelper()
    # handle either a resource dict or just an ID
    # ID is more efficient, as resource dicts can be very large
    if isinstance(resource, six.string_types):
        log.debug(u'run_validation_job: calling resource_show: %s', resource)
        resource = t.get_action('resource_show')({'ignore_auth': True}, {'id': resource})

    if 'id' in resource:
        log.warn(u'Validating resource: %s', resource)
    else:
        log.debug(u'Validating resource dict: %s', resource)
    session = Session
    db_record = None
    try:
        db_record = vsh.updateValidationJobStatus(session, resource['id'], StatusTypes.running)
    except ValidationJobAlreadyRunning as e:
        log.error("Won't run enqueued job %s as job is already running or in invalid state: %s", resource['id'], e)
        return
    except ValidationJobDoesNotExist:
        db_record = vsh.createValidationJob(session, resource['id'])
        db_record = vsh.updateValidationJobStatus(session=session, resource_id=resource['id'],
                                                  status=StatusTypes.running, validationRecord=db_record)

    options = t.config.get(
        u'ckanext.validation.default_validation_options')
    if options:
        options = json.loads(options)
    else:
        options = {}

    resource_options = resource.get(u'validation_options')
    if resource_options and isinstance(resource_options, six.string_types):
        resource_options = json.loads(resource_options)
    if resource_options:
        options.update(resource_options)

    dataset = t.get_action('package_show')(
        {'ignore_auth': True}, {'id': resource['package_id']})

    source = None
    if resource.get(u'url_type') == u'upload':
        upload = uploader.get_resource_uploader(resource)
        if isinstance(upload, uploader.ResourceUpload):
            source = upload.get_path(resource[u'id'])
        else:
            # Upload is not the default implementation (ie it's a cloud storage
            # implementation)
            pass_auth_header = t.asbool(
                t.config.get(u'ckanext.validation.pass_auth_header', True))
            if dataset[u'private'] and pass_auth_header:
                s = requests.Session()
                s.headers.update({
                    u'Authorization': t.config.get(
                        u'ckanext.validation.pass_auth_header_value',
                        _get_site_user_api_key())
                })

                options[u'http_session'] = s

    if not source:
        source = resource[u'url']

    schema = resource.get(u'schema')
    if schema and isinstance(schema, six.string_types):
        if schema.startswith('http'):
            r = requests.get(schema)
            schema = r.json()
        else:
            schema = json.loads(schema)

    _format = resource[u'format'].lower()

    report = _validate_table(source, _format=_format, schema=schema, **options)

    # Hide uploaded files
    for table in report.get('tables', []):
        if table['source'].startswith('/'):
            table['source'] = resource['url']
    for index, warning in enumerate(report.get('warnings', [])):
        report['warnings'][index] = re.sub(r'Table ".*"', 'Table', warning)

    if report['table-count'] > 0:
        status = StatusTypes.success if report[u'valid'] else StatusTypes.failure
        db_record = vsh.updateValidationJobStatus(session, resource['id'], status, report, None, db_record)
    else:
        status = StatusTypes.error
        error_payload = {'message': '\n'.join(report['warnings']) or u'No tables found'}
        db_record = vsh.updateValidationJobStatus(session, resource['id'], status, None, error_payload, db_record)

    # Store result status in resource
    t.get_action('resource_patch')(
        {'ignore_auth': True,
         'user': t.get_action('get_site_user')({'ignore_auth': True})['name'],
         '_validation_performed': True},
        {'id': resource['id'],
         'validation_status': db_record.status,
         'validation_timestamp': db_record.finished.isoformat()})


def _validate_table(source, _format=u'csv', schema=None, **options):

    http_session = options.pop('http_session', None) or requests.Session()

    use_proxy = 'ckan.download_proxy' in t.config
    if use_proxy:
        proxy = t.config.get('ckan.download_proxy')
        log.debug(u'Download resource for validation via proxy: %s', proxy)
        http_session.proxies.update({'http': proxy, 'https': proxy})
    report = validate(source, format=_format, schema=schema, http_session=http_session, **options)

    log.debug(u'Validating source: %s', source)

    return report


def _get_site_user_api_key():

    site_user_name = t.get_action('get_site_user')({'ignore_auth': True}, {})
    site_user = t.get_action('get_site_user')(
        {'ignore_auth': True}, {'id': site_user_name})
    return site_user['apikey']
