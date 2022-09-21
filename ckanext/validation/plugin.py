# encoding: utf-8

import json
import logging
import os

import ckan.plugins.toolkit as tk
import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation

from ckanext.validation import settings
from ckanext.validation.model import tables_exist
from ckanext.validation.helpers import _get_helpers, is_ckan_29
from ckanext.validation.validators import _get_validators
from ckanext.validation import utils
from ckanext.validation.interfaces import IDataValidation
from ckanext.validation.logic.action import _get_actions
from ckanext.validation.logic.auth import _get_auth_functions

log = logging.getLogger(__name__)

if is_ckan_29():
    from .plugin_mixins.flask_plugin import MixinPlugin
else:
    from .plugin_mixins.pylons_plugin import MixinPlugin


class ValidationPlugin(MixinPlugin, p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IValidators)
    p.implements(p.ITranslation, inherit=True)

    # ITranslation
    def i18n_directory(self):
        u'''Change the directory of the .mo translation files'''
        return os.path.join(os.path.dirname(__file__), 'i18n')

    # IConfigurer

    def update_config(self, config_):
        if not tables_exist():
            log.critical(u'''
                The validation extension requires a database setup.
                Validation pages will not be enabled.
                Please run the following to create the database tables:
                ckan validation init-db
                ''')
        else:
            log.debug(u'Validation tables exist')

        tk.add_template_directory(config_, u'templates')
        tk.add_resource(u'assets', 'ckanext-validation')

    # IActions

    def get_actions(self):
        return _get_actions()

    # IAuthFunctions

    def get_auth_functions(self):
        return _get_auth_functions()

    # ITemplateHelpers

    def get_helpers(self):
        return _get_helpers()

    # IResourceController

    def before_create(self, context, data_dict):
        if utils._is_dataset(data_dict):
            return

        data_dict = utils.process_schema_fields(data_dict)

        # if it's a sync mode, it's better run it before creation, because
        # the uploaded file will be here
        import ipdb
        ipdb.set_trace()
        if utils.get_create_mode() == "sync" \
            and utils._is_resource_requires_validation(context, data_dict):
            utils._validate_resource(context, data_dict, new_resource=True)
            import ipdb
            ipdb.set_trace()
            pass

    def after_create(self, context, data_dict):
        if utils._is_dataset(data_dict):
            return

        # if it's an async mode, it's better run it here, because the actual
        # file is uploaded at this stage, so background job could easily access it
        if utils.get_create_mode() == "async" \
            and utils._is_resource_requires_validation(context, data_dict):
            utils._validate_resource(context, data_dict, new_resource=True)

        if data_dict.pop('_success_validation', False):
            utils._create_success_validation_job(data_dict["id"])

    def before_update(self, context, current_resource, updated_resource):
        if utils._is_dataset(updated_resource):
            return

        # avoid circular update, because validation job calls `resource_patch`
        # (which calls package_update)
        if context.pop('_validation_performed', None):
            return

        updated_resource = utils.process_schema_fields(updated_resource)

        # if it's a sync mode, it's better run it before updating, because
        # the new uploaded file will be here
        if utils.get_update_mode() == "sync" \
            and utils._is_updated_resource_requires_validation(
                context, current_resource, updated_resource):
            utils._validate_resource(context, updated_resource)

    def after_update(self, context, data_dict):
        if utils._is_dataset(data_dict):
            return

        if context.pop('_validation_performed', None):
            return

        # if it's an async mode, it's better run it here, because the actual new
        # file is uploaded at this stage, so background job could easily access it
        if utils.get_update_mode() == "async" \
            and utils._is_resource_requires_validation(context, data_dict):
            utils._validate_resource(context, data_dict, new_resource=True)

        if data_dict.pop('_success_validation', False):
            utils._create_success_validation_job(data_dict["id"])

    # IPackageController

    def before_index(self, index_dict):

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
        return _get_validators()
