# encoding: utf-8

import logging
import json
import requests
from six import string_types

try:
    from frictionless import validate, Report, system, Schema, Dialect, Check
    use_frictionless = True
except ImportError:
    from goodtables import validate
    use_frictionless = False

import ckantoolkit as t

from . import settings as s

log = logging.getLogger(__name__)


def is_api_call():
    controller, action = t.get_endpoint()

    resource_edit = (controller == "resource" and action == "edit") or (
        controller == "package" and action == "resource_edit"
    )
    resource_create = action == "new_resource"
    package_edit = (controller == "dataset" and action == "edit") or (
        controller == "package" and action == "edit"
    )

    return not (resource_edit or resource_create or package_edit)


def is_dataset(data_dict):
    """Checks if data_dict is dataset dict"""
    return (u'creator_user_id' in data_dict or u'owner_org' in data_dict
            or u'resources' in data_dict
            or data_dict.get(u'type') == u'dataset')


def get_resource_validation_options(resource_data):
    """Prepares resource validation options by combining the default ones
    and specific ones from `validation_options` field.

    Args:
        resource_data (dict): resource data

    Returns:
        dict: validation options dict
    """
    options = s.get_default_validation_options()
    options['http_session'] = _get_session(resource_data)
    resource_options = resource_data.get(u'validation_options')

    if resource_options and isinstance(resource_options, string_types):
        resource_options = json.loads(resource_options)

    if resource_options:
        options.update(resource_options)

    return options


def _get_session(resource_data):
    if 'package_id' not in resource_data:
        resource_data = t.get_action('resource_show')(
            {'ignore_auth': True}, {'id': resource_data['id']})
    dataset = t.get_action('package_show')(
        {'ignore_auth': True}, {'id': resource_data['package_id']})

    pass_auth_header = t.asbool(
        t.config.get(s.PASS_AUTH_HEADER, s.PASS_AUTH_HEADER_DEFAULT))

    if dataset[u'private'] and pass_auth_header:
        _session = requests.Session()
        _session.headers.update({
            u'Authorization':
            t.config.get(s.PASS_AUTH_HEADER_VALUE, get_site_user()['apikey'])
        })

        return _session


def get_site_user():
    context = {'ignore_auth': True}
    site_user_name = t.get_action('get_site_user')(context, {})
    return t.get_action('get_site_user')(context, {'id': site_user_name})


def validate_table(source, _format=u'csv', schema=None, **options):
    http_session = options.pop('http_session', None) or requests.Session()

    use_proxy = 'ckan.download_proxy' in t.config
    if use_proxy:
        proxy = t.config.get('ckan.download_proxy')
        log.debug(u'Download resource for validation via proxy: %s', proxy)
        http_session.proxies.update({'http': proxy, 'https': proxy})

    log.debug(u'Validating source: %s', source)
    if use_frictionless:
        # This option is needed to allow Frictionless Framework to validate absolute paths
        frictionless_context = {'trusted': True, 'http_session': http_session}
        resource_schema = Schema.from_descriptor(schema) if schema else None

        # Load the Resource Dialect as described in https://framework.frictionlessdata.io/docs/framework/dialect.html
        if 'dialect' in options:
            dialect = Dialect.from_descriptor(options['dialect'])
            options['dialect'] = dialect

        # Load the list of checks and its parameters declaratively as in https://framework.frictionlessdata.io/docs/checks/table.html
        if 'checks' in options:
            checklist = [Check.from_descriptor(c) for c in options['checks']]
            options['checks'] = checklist

        with system.use_context(**frictionless_context):
            report = validate(source, format=_format, schema=resource_schema, **options)
            if type(report) == Report:
                report = report.to_dict()
    else:
        report = validate(source, format=_format, schema=schema, http_session=http_session, **options)

    return report
