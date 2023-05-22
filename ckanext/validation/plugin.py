# encoding: utf-8

from cgi import FieldStorage
from datetime import datetime as dt
from io import BytesIO
import json
import logging
import os
import requests
from requests.exceptions import RequestException
from six import ensure_str, string_types

from ckan import model
from ckan.lib import uploader
from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as p

import ckantoolkit as t

from . import blueprints, cli, logic, settings as s, utils, validators
from .helpers import _get_helpers, is_url_valid
from .interfaces import IDataValidation
from .model import tables_exist
from .validators import resource_schema_validator
from .validation_status_helper import ValidationStatusHelper, StatusTypes

log = logging.getLogger(__name__)


def _get_default_schema(package_id):
    """Dataset could have a default_schema, that could be used
    to validate resource"""

    dataset = model.Package.get(package_id)

    if not dataset:
        return

    return dataset.extras.get(u'default_data_schema')


def _is_resource_could_be_validated(context, data_dict):
    """Check if new resource could be validated"""
    for plugin in p.PluginImplementations(IDataValidation):
        if not plugin.can_validate(context, data_dict):
            log.debug('Skipping validation for new resource')
            return False

    if not data_dict.get(u'format'):
        log.info("Missing resource format. Skipping validation")
        return False

    res_format = data_dict.get(u'format', u'').lower()
    supportable_format = res_format in s.get_supported_formats()

    if supportable_format and (data_dict.get(u'url_type') == u'upload'
                               or data_dict.get(u'upload')
                               or data_dict.get(u'url')):
        return True

    return False


def _is_resource_requires_validation(context, old_resource, new_resource):
    """Compares current resource data with updated resource data to understand
    do we need to re-validate it"""
    res_id = new_resource["id"]
    schema = new_resource.get(u'schema')
    schema_aligned = t.asbool(new_resource.get('align_default_schema'))

    for plugin in p.PluginImplementations(IDataValidation):
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

    if is_format_changed and new_format in s.get_supported_formats():
        log.info("Format has been changed. Validation required")
        return True

    if old_resource.get("validation_options") != new_resource.get("validation_options"):
        log.info("Validation options have been updated. Validation required")
        return True

    return False


def _validate_resource(context, data_dict, new_resource=False):
    create_mode = s.get_create_mode(context, data_dict)
    update_mode = s.get_update_mode(context, data_dict)

    mode = create_mode if new_resource else update_mode

    if mode == s.SYNC_MODE:
        _run_sync_validation(data_dict)
    elif mode == s.ASYNC_MODE:
        _run_async_validation(data_dict["id"])


def _run_sync_validation(resource_data):
    """If we are using sync validation (validation on update/create resource)
    We must do it before the actual file upload, because if file is invalid
    we don't want to replace the old one

    Args:
        resource_data (dict): new/updated resource data
    """
    schema = resource_data.get('schema')

    if t.asbool(resource_data.get('align_default_schema')):
        schema = _get_default_schema(resource_data["package_id"])

    if schema and isinstance(schema, string_types):
        schema = schema if is_url_valid(schema) else json.loads(schema)

    _format = resource_data.get('format', '').lower()
    options = utils.get_resource_validation_options(resource_data)

    new_file = resource_data.get('upload')

    if _is_uploaded_file(new_file):
        source = _get_new_file_stream(new_file)
    else:
        if is_url_valid(resource_data['url']):
            source = resource_data['url']
        else:
            source = _get_uploaded_resource_path(resource_data)

    report = utils.validate_table(
        source,
        _format=_format,
        schema=schema or None,
        **options
    )

    if report and not report['valid']:
        for table in report.get('tables', []):
            table['source'] = resource_data['url']

        raise t.ValidationError({u'validation': [report]})
    else:
        _table_count = report.get('table-count', 0) > 0

        resource_data[
            'validation_status'] = StatusTypes.success if _table_count else ""
        resource_data['validation_timestamp'] = str(
            dt.utcnow()) if _table_count else ""
        resource_data['_success_validation'] = True


def _data_dict_is_dataset(data_dict):
    return (
        u'creator_user_id' in data_dict
        or u'owner_org' in data_dict
        or u'resources' in data_dict
        or data_dict.get(u'type') == u'dataset')


class ValidationPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IValidators)
    p.implements(p.ITranslation, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IClick)

    # IBlueprint

    def get_blueprint(self):
        return blueprints.get_blueprints()

    # IClick

    def get_commands(self):
        return cli.get_commands()

    # ITranslation
    def i18n_directory(self):
        u'''Change the directory of the .mo translation files'''
        return os.path.join(
            os.path.dirname(__file__),
            'i18n'
        )

    # IConfigurer

    def update_config(self, config_):
        if not tables_exist():
            init_command = 'ckan validation init-db'
            log.critical(u'''
The validation extension requires a database setup.
Validation pages will not be enabled.
Please run the following to create the database tables:
    %s''', init_command)

        t.add_template_directory(config_, u'templates')
        t.add_resource(u'webassets', 'ckanext-validation')

    # IActions

    def get_actions(self):
        return logic.get_actions()

    # IAuthFunctions

    def get_auth_functions(self):
        return logic.get_auth_functions()

    # ITemplateHelpers

    def get_helpers(self):
        return _get_helpers()

    # IResourceController

    def _process_schema_fields(self, data_dict):
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

        if _is_uploaded_file(schema_upload):
            data_dict[u'schema'] = ensure_str(
                uploader._get_underlying_file(schema_upload).read())
        elif schema_url:
            if not is_url_valid(schema_url):
                raise t.ValidationError({u'schema_url': ['Must be a valid URL']})

            try:
                resp = requests.get(schema_url)
                schema = resp.json()
            except (ValueError, RequestException):
                raise t.ValidationError(
                    {u"schema_url": ["Can't read a valid schema from url"]})

            data_dict[u'schema'] = schema
        elif schema_json:
            data_dict[u'schema'] = schema_json

        if not data_dict.get('schema'):
            return data_dict

        try:
            resource_schema_validator(data_dict[u'schema'], {})
        except t.Invalid:
            raise t.ValidationError({u'schema': ['Schema is invalid']})

        return data_dict

    # CKAN < 2.10
    def before_create(self, context, data_dict):
        if not _data_dict_is_dataset(data_dict):
            return self.before_resource_create(context, data_dict)

    # CKAN >= 2.10
    def before_resource_create(self, context, data_dict):
        context["_resource_validation"] = True

        data_dict = self._process_schema_fields(data_dict)

        if s.get_create_mode(context, data_dict) == s.ASYNC_MODE:
            return

        if _is_resource_could_be_validated(context, data_dict):
            _validate_resource(context, data_dict, new_resource=True)

    # CKAN < 2.10
    def after_create(self, context, data_dict):
        if _data_dict_is_dataset(data_dict):
            return self.after_dataset_create(context, data_dict)
        else:
            return self.after_resource_create(context, data_dict)

    # CKAN >= 2.10
    def after_resource_create(self, context, data_dict):
        if data_dict.pop('_success_validation', False):
            return create_success_validation_job(data_dict["id"])

        if s.get_create_mode(context, data_dict) == s.SYNC_MODE:
            return

        if _is_resource_could_be_validated(context, data_dict):
            _validate_resource(context, data_dict, new_resource=True)

    # CKAN < 2.10
    def before_update(self, context, current_resource, updated_resource):
        if not _data_dict_is_dataset(current_resource):
            return self.before_resource_update(context, current_resource, updated_resource)

    # CKAN >= 2.10
    def before_resource_update(self, context, current_resource, updated_resource):
        context['_resource_validation'] = True
        # avoid circular update, because validation job calls `resource_patch`
        # (which calls package_update)
        if context.get('_validation_performed'):
            return

        updated_resource = self._process_schema_fields(updated_resource)
        needs_validation = _is_resource_requires_validation(
            context, current_resource, updated_resource)

        if not needs_validation:
            updated_resource['_do_not_validate'] = True
            return

        # if it's a sync mode, it's better run it before updating, because
        # the new uploaded file will be here
        if s.get_update_mode(context, updated_resource) == s.SYNC_MODE:
            _validate_resource(context, updated_resource)
        else:
            # if it's an async mode, gather ID's and use it in `after_update`
            # because only here we are able to compare current data with new
            context.setdefault("_resources_to_validate", [])

            if needs_validation:
                context['_resources_to_validate'].append(
                    updated_resource["id"])

    # CKAN < 2.10
    def after_update(self, context, data_dict):
        if _data_dict_is_dataset(data_dict):
            return self.after_dataset_update(context, data_dict)
        else:
            return self.after_resource_update(context, data_dict)

    # CKAN >= 2.10
    def after_dataset_update(self, context, data_dict):
        if context.pop('_validation_performed', None) \
                or context.pop('_resource_validation', None):
            return

        for resource in data_dict.get('resources', []):
            if resource.pop(u'_do_not_validate', False) \
                    or resource.pop('_success_validation', False):
                continue

            if not _is_resource_could_be_validated(context, resource):
                continue

            _validate_resource(context, resource)

    def after_resource_update(self, context, data_dict):
        context.pop('_resource_validation', None)

        if context.pop('_validation_performed', None) \
                or data_dict.pop(u'_do_not_validate', False) \
                or data_dict.pop('_success_validation', False):
            return

        validation_possible = _is_resource_could_be_validated(
            context, data_dict)

        if not validation_possible:
            return

        resource_id = data_dict[u'id']

        if resource_id not in context.get('_resources_to_validate', []):
            return

        _validate_resource(context, data_dict)

        context.pop('_resources_to_validate', None)

    # CKAN < 2.10
    def before_delete(self, context, resource, resources):
        if not _data_dict_is_dataset(resource):
            self.before_resource_delete(context, resource, resources)

    # CKAN >= 2.10
    def before_resource_delete(self, context, resource, resources):
        context['_resource_validation'] = True

    # CKAN >= 2.10
    def after_dataset_create(self, context, data_dict):
        for resource in data_dict.get(u'resources', []):
            if _is_resource_could_be_validated(context, resource):
                _validate_resource(context, resource)

    def before_index(self, index_dict):
        if (_data_dict_is_dataset(index_dict)):
            return self.before_dataset_index(index_dict)

    # CKAN >= 2.10
    def before_dataset_index(self, index_dict):

        res_status = []
        dataset_dict = json.loads(index_dict['validated_data_dict'])
        for resource in dataset_dict.get('resources', []):
            if resource.get('validation_status'):
                res_status.append(resource['validation_status'])

        if res_status:
            index_dict['vocab_validation_status'] = res_status

        return index_dict

    # IValidators

    def get_validators(self):
        return validators.get_validators()


def _get_new_file_stream(file):
    if isinstance(file, FieldStorage):
        file = file.file

    stream = BytesIO(file.read())
    file.seek(0)

    return stream


def _is_uploaded_file(upload):
    return isinstance(upload,
                      uploader.ALLOWED_UPLOAD_TYPES) and upload.filename


def _get_uploaded_resource_path(resource_data):
    """Get a path for uploaded resource. Supports a default ResourceUpload and
    ckanext-s3filestore S3ResourceUploader."""
    upload = uploader.get_resource_uploader(resource_data)
    path = None

    if isinstance(upload, uploader.ResourceUpload):
        path = upload.get_path(resource_data['id'])
    else:
        try:
            from ckanext.s3filestore.uploader import S3ResourceUploader
        except Exception:
            return path

        if isinstance(upload, S3ResourceUploader):
            filename = os.path.basename(resource_data["url"])
            key_path = upload.get_path(resource_data["id"], filename)
            path = upload.get_signed_url_to_key(key_path, {
                'ResponseContentDisposition':
                'attachment; filename=' + filename,
            })

    return path


def _run_async_validation(resource_id):
    try:
        t.get_action(u'resource_validation_run')(
            {u'ignore_auth': True},
            {u'resource_id': resource_id,
             u'async': True})
    except t.ValidationError as e:
        log.warning(
            u'Could not run validation for resource %s: %s',
            resource_id, e)


def create_success_validation_job(resource_id):
    """Create a success job after validation passed
    We have to do it, because at the resource creation stage we don't have
    a resource_id, so first we are validating file and if it's valid - we are
    creating resource, and at the `after_create` & `after_update` stage creating
    a success validation record."""
    vsh = ValidationStatusHelper()

    record = vsh.createValidationJob(model.Session, resource_id)
    record = vsh.updateValidationJobStatus(session=model.Session,
                                           resource_id=resource_id,
                                           status=StatusTypes.success,
                                           validationRecord=record)
