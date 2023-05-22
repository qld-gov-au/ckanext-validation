# encoding: utf-8

import logging
import json
import re

import requests
from six import string_types

from ckan.model import Session
import ckan.lib.uploader as uploader

import ckantoolkit as t

from ckanext.validation import utils
from ckanext.validation.validation_status_helper import (ValidationStatusHelper, ValidationJobDoesNotExist,
                                                         ValidationJobAlreadyRunning, StatusTypes)

log = logging.getLogger(__name__)


def run_validation_job(resource):
    vsh = ValidationStatusHelper()
    # handle either a resource dict or just an ID
    # ID is more efficient, as resource dicts can be very large
    if isinstance(resource, string_types):
        log.debug(u'run_validation_job: calling resource_show: %s', resource)
        resource = t.get_action('resource_show')({'ignore_auth': True}, {'id': resource})

    resource_id = resource.get('id')
    if resource_id:
        log.debug(u'Validating resource: %s', resource_id)
    else:
        log.debug(u'Validating resource dict: %s', resource)
    validation_record = None
    try:
        validation_record = vsh.updateValidationJobStatus(Session, resource_id, StatusTypes.running)
    except ValidationJobAlreadyRunning as e:
        log.error("Won't run enqueued job %s as job is already running or in invalid state: %s", resource['id'], e)
        return
    except ValidationJobDoesNotExist:
        validation_record = vsh.createValidationJob(Session, resource['id'])
        validation_record = vsh.updateValidationJobStatus(
            session=Session, resource_id=resource_id,
            status=StatusTypes.running, validationRecord=validation_record)

    options = utils.get_resource_validation_options(resource)

    source = None
    if resource.get(u'url_type') == u'upload':
        upload = uploader.get_resource_uploader(resource)
        if isinstance(upload, uploader.ResourceUpload):
            source = upload.get_path(resource[u'id'])

    if not source:
        source = resource[u'url']

    schema = resource.get(u'schema')
    if schema and isinstance(schema, string_types):
        if schema.startswith('http'):
            r = requests.get(schema)
            schema = r.json()
        else:
            schema = json.loads(schema)

    _format = resource[u'format'].lower()

    report = utils.validate_table(source, _format=_format, schema=schema, **options)

    # Hide uploaded files
    for table in report.get('tables', []):
        if table['source'].startswith('/'):
            table['source'] = resource['url']
    for index, warning in enumerate(report.get('warnings', [])):
        report['warnings'][index] = re.sub(r'Table ".*"', 'Table', warning)

    if report['table-count'] > 0:
        status = StatusTypes.success if report[u'valid'] else StatusTypes.failure
        validation_record = vsh.updateValidationJobStatus(Session, resource['id'], status, report, None, validation_record)
    else:
        status = StatusTypes.error
        error_payload = {'message': '\n'.join(report['warnings']) or u'No tables found'}
        validation_record = vsh.updateValidationJobStatus(Session, resource['id'], status, None, error_payload, validation_record)

    # Store result status in resource
    t.get_action('resource_patch')(
        {'ignore_auth': True,
         'user': utils.get_site_user()['name'],
         '_validation_performed': True},
        {'id': resource['id'],
         'validation_status': validation_record.status,
         'validation_timestamp': validation_record.finished.isoformat()})
