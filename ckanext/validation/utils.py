# encoding: utf-8

import os
import logging
import json
from io import BytesIO
from datetime import datetime as dt
from cgi import FieldStorage

import requests
import ckantoolkit as tk
from requests.exceptions import RequestException
from goodtables import validate
from tabulator.config import PARSERS
from six import string_types

import ckan.plugins as plugins
import ckan.lib.uploader as uploader
from ckan.model import Session

import ckanext.validation.settings as s
from ckanext.validation.interfaces import IDataValidation
from ckanext.validation.validation_status_helper import ValidationStatusHelper, StatusTypes
from ckanext.validation.helpers import is_url_valid

log = logging.getLogger(__name__)


def get_update_mode(context, resource_data):
    is_async = tk.asbool(tk.config.get(s.ASYNC_UPDATE_KEY))

    mode = s.ASYNC_MODE if is_async else s.SYNC_MODE

    for plugin in plugins.PluginImplementations(IDataValidation):
        mode = plugin.set_update_mode(context, resource_data, mode)

    assert mode in s.SUPPORTED_MODES, u"Mode '{}' is not supported".format(
        mode)

    return mode


def get_create_mode(context, resource_data):
    is_async = tk.asbool(tk.config.get(s.ASYNC_CREATE_KEY))

    mode = s.ASYNC_MODE if is_async else s.SYNC_MODE

    for plugin in plugins.PluginImplementations(IDataValidation):
        mode = plugin.set_create_mode(context, resource_data, mode)

    assert mode in s.SUPPORTED_MODES, u"Mode '{}' is not supported".format(
        mode)

    return mode


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

    if is_uploaded_file(schema_upload):
        data_dict[u'schema'] = uploader._get_underlying_file(
            schema_upload).read()

    elif schema_url:
        if not is_url_valid(schema_url):
            raise tk.ValidationError({u'schema_url': ['Must be a valid URL']})

        try:
            resp = requests.get(schema_url)
            schema = resp.json()
        except (ValueError, RequestException):
            raise tk.ValidationError(
                {u'schema_url': ['Can\'t read a valid schema from url']})

        data_dict[u'schema'] = schema

    elif schema_json:
        data_dict[u'schema'] = schema_json

    return data_dict


def validate_resource(context, data_dict, new_resource=False):
    create_mode = get_create_mode(context, data_dict)
    update_mode = get_update_mode(context, data_dict)

    mode = create_mode if new_resource else update_mode

    if mode == s.SYNC_MODE:
        run_sync_validation(data_dict)
    elif mode == s.ASYNC_MODE:
        run_async_validation(data_dict["id"])


def run_sync_validation(resource_data):
    """If we are using sync validation (validation on update/create resource)
    We must do it before the actual file upload, because if file is invalid
    we don't want to replace the old one

    Args:
        resource_data (dict): new/updated resource data
    """
    schema = resource_data.get('schema')

    if tk.asbool(resource_data.get('align_default_schema')):
        schema = _get_default_schema(resource_data["package_id"])

    if schema and isinstance(schema, string_types):
        schema = schema if is_url_valid(schema) else json.loads(schema)

    _format = resource_data.get('format', '').lower()
    options = get_resource_validation_options(resource_data)

    new_file = resource_data.get('upload')

    if is_uploaded_file(new_file):
        source = _get_new_file_stream(new_file)
    else:
        if resource_data.get('url_type') == u'upload':
            upload = uploader.get_resource_uploader(resource_data)

            if isinstance(upload, uploader.ResourceUpload):
                source = upload.get_path(resource_data["id"])
            else:
                source = resource_data['url']
        else:
            source = resource_data['url']

    report = validate(source,
                      format=_format,
                      schema=schema or None,
                      http_session=_get_session(resource_data),
                      **options)

    if report and not report['valid']:
        for table in report.get('tables', []):
            table['source'] = resource_data['url']

        raise tk.ValidationError({u'validation': [report]})
    else:
        _table_count = report.get('table-count', 0) > 0

        resource_data[
            'validation_status'] = StatusTypes.success if _table_count else ""
        resource_data['validation_timestamp'] = str(
            dt.now()) if _table_count else ""
        resource_data['_success_validation'] = True


def _get_session(resource_data):
    dataset = tk.get_action('package_show')({
        'user': get_site_user()['name']
    }, {
        'id': resource_data['package_id']
    })

    pass_auth_header = tk.asbool(
        tk.config.get(s.PASS_AUTH_HEADER, s.PASS_AUTH_HEADER_DEFAULT))

    if dataset[u'private'] and pass_auth_header:
        _session = requests.Session()
        _session.headers.update({
            u'Authorization':
            tk.config.get(s.PASS_AUTH_HEADER_VALUE, get_site_user_api_key())
        })

        return _session


def _get_new_file_stream(file):
    if isinstance(file, FieldStorage):
        file = file.file

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


def is_resource_could_be_validated(context, data_dict):
    """Check if new resource could be validated"""
    for plugin in plugins.PluginImplementations(IDataValidation):
        if not plugin.can_validate(context, data_dict):
            log.debug('Skipping validation for new resource')
            return False

    if not data_dict.get(u'format'):
        log.info("Missing resource format. Skipping validation")
        return False

    res_format = data_dict.get(u'format', u'').lower()
    supportable_format = res_format in get_supported_formats()

    if supportable_format and (data_dict.get(u'url_type') == u'upload'
                               or data_dict.get(u'upload')
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


def is_resource_requires_validation(context, old_resource, new_resource):
    """Compares current resource data with updated resource data to understand
    do we need to re-validate it"""
    res_id = new_resource["id"]
    schema = new_resource.get(u'schema')
    schema_aligned = tk.asbool(new_resource.get('align_default_schema'))

    if schema_aligned and is_api_call():
        raise tk.ValidationError({
            u'align_default_schema':
            [tk._(u"This field couldn't be updated via API")]
        })

    for plugin in plugins.PluginImplementations(IDataValidation):
        if not plugin.can_validate(context, new_resource):
            log.debug(u"Skipping validation for resource {}".format(res_id))
            return False

    if not new_resource.get(u'format'):
        log.info(u"Missing resource format. Skipping validation")
        return False

    if new_resource.get(u'upload'):
        log.info(u"New resource file. Validation required")
        return True

    if new_resource.get(u'url') != old_resource.get(u'url'):
        log.info(u"New resource url. Validation required")
        return True

    if (schema != old_resource.get(u'schema')) or schema_aligned:
        log.info("Schema has been updated. Validation required")
        return True

    old_format = old_resource.get(u'format', u'').lower()
    new_format = new_resource.get(u'format', u'').lower()
    is_format_changed = new_format != old_format

    if is_format_changed and new_format in get_supported_formats():
        log.info("Format has been changed. Validation required")
        return True

    if (old_resource.get(u'validation_options')
            != new_resource.get(u'validation_options')):
        log.info("Validation options have been updated. Validation required")
        return True

    return False


def is_api_call():
    controller, action = tk.get_endpoint()

    resource_edit = ((controller == "resource" and action == "edit")
                     or (controller == "package" and action == "resource_edit"))
    resource_create = action == "new_resource"

    return False if (resource_edit or resource_create) else True


def is_dataset(data_dict):
    """Checks if data_dict is dataset dict"""
    return (u'creator_user_id' in data_dict or u'owner_org' in data_dict
            or u'resources' in data_dict
            or data_dict.get(u'type') == u'dataset')


def create_success_validation_job(resource_id):
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


def get_resource_validation_options(resource_data):
    """Prepares resource validation options by combining the default ones
    and specific ones from `validation_options` field.

    Args:
        resource_data (dict): resource data

    Returns:
        dict: validation options dict
    """
    options = get_default_validation_options()
    resource_options = resource_data.get(u'validation_options')

    if resource_options and isinstance(resource_options, string_types):
        resource_options = json.loads(resource_options)

    if resource_options:
        options.update(resource_options)

    return options


def get_site_user():
    context = {'ignore_auth': True}
    site_user_name = tk.get_action('get_site_user')(context, {})
    return tk.get_action('get_site_user')(context, {'id': site_user_name})


def get_site_user_api_key():
    return get_site_user()['apikey']


def get_supported_formats():
    """Returns a list of supported formats to validate.
    We use a tabulator to parse the file contents, so only those formats for
    which a parser exists are supported

    Returns:
        list[str]: supported format list
    """
    supported_formats = [
        _format.lower()
        for _format in tk.aslist(tk.config.get(s.SUPPORTED_FORMATS_KEY))
    ]

    for _format in supported_formats:
        assert _format in PARSERS, "Format {} is not supported".format(_format)

    return supported_formats or s.DEFAULT_SUPPORTED_FORMATS


def get_default_validation_options():
    """Return a default validation options

    Returns:
        dict[str, Any]: validation options dictionary
    """
    default_options = tk.config.get(s.DEFAULT_VALIDATION_OPTIONS_KEY)
    return json.loads(default_options) if default_options else {}


def is_uploaded_file(upload):
    return isinstance(upload,
                      uploader.ALLOWED_UPLOAD_TYPES) and upload.filename
