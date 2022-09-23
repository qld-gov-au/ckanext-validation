import os
import logging
import json
from io import BytesIO
from datetime import datetime as dt

import requests
from goodtables import validate
from six import string_types

import ckan.plugins.toolkit as tk
import ckan.plugins as plugins
from ckan.model import Session
from ckan.common import asbool, config
from ckan.lib.uploader import (ALLOWED_UPLOAD_TYPES, _get_underlying_file,
                               get_resource_uploader, ResourceUpload)

import ckanext.validation.settings as settings
from ckanext.validation.interfaces import IDataValidation
from ckanext.validation.jobs import run_validation_job, _get_site_user_api_key
from ckanext.validation.validation_status_helper import ValidationStatusHelper, StatusTypes

log = logging.getLogger(__name__)


def get_update_mode():
    if asbool(config.get(u'ckanext.validation.run_on_update_sync', False)):
        return u'sync'
    elif asbool(config.get(u'ckanext.validation.run_on_update_async', True)):
        return u'async'
    else:
        return None


def get_create_mode():
    if asbool(config.get(u'ckanext.validation.run_on_create_sync', False)):
        return u'sync'
    elif asbool(config.get(u'ckanext.validation.run_on_create_async', True)):
        return u'async'
    else:
        return None


def process_schema_fields(data_dict):
    u'''
    Normalize the different ways of providing the `schema` field

    1. If `schema_upload` is provided and it's a valid file, the contents
        are read into `schema`.
    2. If `schema_url` is provided and looks like a valid URL, it's copied
        to `schema`
    3. If `schema_json` is provided, it's copied to `schema`.

    All the 3 `schema_*` fields are removed from the data_dict.
    Note that the data_dict still needs to pass validation
    '''

    schema_upload = data_dict.pop(u'schema_upload', None)
    schema_url = data_dict.pop(u'schema_url', None)
    schema_json = data_dict.pop(u'schema_json', None)

    if isinstance(schema_upload, ALLOWED_UPLOAD_TYPES) \
            and schema_upload.filename:
        data_dict[u'schema'] = _get_underlying_file(schema_upload).read()
    elif schema_url:
        if (not isinstance(schema_url, string_types)
                or not schema_url.lower()[:4] == u'http'):
            raise tk.ValidationError({u'schema_url': ['Must be a valid URL']})
        data_dict[u'schema'] = schema_url
    elif schema_json:
        data_dict[u'schema'] = schema_json

    return data_dict


def _get_missing_fields_from_current(current, new):
    new['package_id'] = current['package_id']


def _validate_resource(context, data_dict, new_resource=False):
    mode = get_create_mode() if new_resource else get_update_mode()

    if mode == "sync":
        run_sync_validation(data_dict)
    elif mode == "async":
        run_async_validation(data_dict["id"])
    else:
        log.error("Validation mod isn't set. Skipping validation")


def run_sync_validation(resource_data):
    """If we are using sync validation (validation on update/create resource)
    We must do it before the actual file upload, because if file is invalid
    we don't want to replace the old one

    Args:
        resource_data (dict): new/updated resource data
    """
    schema = resource_data.get('schema')

    if asbool(resource_data.get('align_default_schema')):
        schema = _get_default_schema(resource_data["package_id"])

    if schema and isinstance(schema, string_types):
        schema = json.loads(schema)

    _format = resource_data.get('format', '').lower()
    options = _get_resource_validation_options(resource_data)
    new_file = resource_data.get('upload')

    if new_file:
        source = _get_new_file_stream(new_file)
    else:
        if resource_data.get('url_type') == u'upload':
            upload = get_resource_uploader(resource_data)

            if isinstance(upload, ResourceUpload):
                source = upload.get_path(resource_data["id"])
            else:
                source = resource_data['url']
        else:
            source = resource_data['url']

    report = validate(source,
                      format=_format,
                      schema=schema,
                      http_session=_get_session(resource_data),
                      **options)

    if report and not report['valid']:
        for table in report.get('tables', []):
            table['source'] = resource_data['url']

        raise tk.ValidationError({u'validation': [report]})
    else:
        _table_count = report.get('table-count', 0) > 0

        resource_data['validation_status'] = StatusTypes.success if _table_count else ""
        resource_data['validation_timestamp'] = str(dt.now()) if _table_count else ""
        resource_data['_success_validation'] = True


def _get_resource_validation_options(resource_data):
    options = config.get(u'ckanext.validation.default_validation_options')

    if options:
        options = json.loads(options)
    else:
        options = {}

    resource_options = resource_data.get(u'validation_options')

    if resource_options and isinstance(resource_options, string_types):
        resource_options = json.loads(resource_options)

    if resource_options:
        options.update(resource_options)

    return options


def _get_session(resource_data):
    dataset = tk.get_action('package_show')({
        'ignore_auth': True
    }, {
        'id': resource_data['package_id']
    })

    pass_auth_header = asbool(
        config.get(u'ckanext.validation.pass_auth_header', True))
    if dataset[u'private'] and pass_auth_header:
        _session = requests.Session()
        _session.headers.update({
            u'Authorization':
            config.get(u'ckanext.validation.pass_auth_header_value',
                       _get_site_user_api_key())
        })

        return _session


def _get_new_file_stream(file):
    stream = BytesIO(file.read())
    file.seek(0, os.SEEK_END)

    return stream


def run_async_validation(resource_id):
    context = {u'ignore_auth': True}
    data_dict = {u'resource_id': resource_id, u'async': True}

    try:
        tk.get_action(u'resource_validation_run')(context, data_dict)
    except tk.ValidationError as e:
        log.warning(u'Could not run validation for resource {}: {}'.format(
            resource_id, e))


def _is_resource_requires_validation(context, data_dict):
    """Check if new resource requires validation"""
    schema = data_dict.get(u'schema')

    if asbool(data_dict.get('align_default_schema')):
        schema = _get_default_schema(data_dict["package_id"])

    if not schema:
        log.info("Missing schema. Skipping validation")
        return False

    if not data_dict.get(u'format'):
        return False

    for plugin in plugins.PluginImplementations(IDataValidation):
        if not plugin.can_validate(context, data_dict):
            log.debug('Skipping validation for new resource')
            return False

    res_format = data_dict.get(u'format', u'').lower()
    supportable_format = res_format in settings.SUPPORTED_FORMATS

    if supportable_format and (data_dict.get(u'url_type') == u'upload'
                               or data_dict.get(u'url')):
        return True

    return False


def _get_default_schema(package_id):
    """Dataset could have a default_schema, that could be used
    to validate resource"""
    dataset = tk.get_action(u'package_show')({
        'ignore_auth': True
    }, {
        'id': package_id
    })

    return dataset.get(u'default_data_schema')


def _is_updated_resource_requires_validation(context, old_resource,
                                             new_resource):
    res_id = new_resource["id"]
    is_creation = not old_resource

    schema = new_resource.get(u'schema')

    if not schema:
        log.info("Missing resource schema. Skipping validation")
        return False

    if not new_resource.get(u'format'):
        return False

    for plugin in plugins.PluginImplementations(IDataValidation):
        if not plugin.can_validate(context, new_resource):
            log.debug('Skipping validation for resource {}'.format(res_id))
            return False

    if new_resource.get(u'upload'):
        return True

    if is_creation:
        return True

    if new_resource.get(u'url') != old_resource.get(u'url'):
        return True

    new_schema = new_resource.get(u'schema')
    if new_schema and new_schema != old_resource.get(u'schema'):
        return True

    if asbool(new_resource.get('align_default_schema')):
        return True

    old_format = old_resource.get(u'format', u'').lower()
    new_format = new_resource.get(u'format', u'').lower()
    is_format_changed = new_format != old_format
    if is_format_changed and new_format in settings.SUPPORTED_FORMATS:
        return True

    return False


def _is_dataset(data_dict):
    """Checks if data_dict is dataset"""
    return (u'creator_user_id' in data_dict or u'owner_org' in data_dict
            or u'resources' in data_dict
            or data_dict.get(u'type') == u'dataset')


def _create_success_validation_job(resource_id):
    """Create a success job after validation passed
    We have to do it, because at the resource creation stage we don't have
    a resource_id, so first we are validating file and if it's valid - we are
    creating resource, and at the `after_create` & `after_update` stage creating
    a success validation record."""
    vsh = ValidationStatusHelper()

    record = vsh.createValidationJob(Session, resource_id)
    record = vsh.updateValidationJobStatus(session=Session,
                                           resource_id=resource_id,
                                           status=StatusTypes.success,
                                           validationRecord=record)
