# encoding: utf-8

import mock
import pytest

from ckan import plugins as p
from ckan.tests import helpers, factories

import ckanext.validation.settings as settings
import ckanext.validation.tests.helpers as validation_helpers
from ckanext.validation.interfaces import IDataValidation


class TestPlugin(p.SingletonPlugin):

    p.implements(IDataValidation, inherit=True)

    calls = 0

    def reset_counter(self):
        self.calls = 0

    def can_validate(self, context, data_dict):
        self.calls += 1

        if data_dict.get('do_not_validate') == True:
            return False

        return True

    def set_create_mode(self, context, data_dict, current_mode):
        is_async = data_dict.get('async')
        return settings.ASYNC_MODE if is_async == True else current_mode

    def set_update_mode(self, context, data_dict, current_mode):
        is_async = data_dict.get('async')
        return settings.ASYNC_MODE if is_async == True else current_mode


def _get_plugin_calls():
    for plugin in p.PluginImplementations(IDataValidation):
        return plugin.calls


class BaseTestInterfaces(object):

    def setup(self):
        for plugin in p.PluginImplementations(IDataValidation):
            return plugin.reset_counter()


@pytest.mark.usefixtures("clean_db", "validation_setup")
@mock.patch(validation_helpers.MOCK_SYNC_VALIDATE,
            return_value=validation_helpers.VALID_REPORT)
class TestInterfaceSync(BaseTestInterfaces):

    def test_can_validate_called_on_create_sync(self, mock_validation, resource_factory):
        """Plugin must be called once for SYNC mode on create
        1. resource before_create
        """
        resource_factory()

        assert _get_plugin_calls() == 1
        assert mock_validation.called

    def test_can_validate_called_on_create_sync_no_validation(
            self, mock_validation, resource_factory):
        """Plugin must be called once for SYNC mode on create
        1. resource before_create
        """
        resource_factory(do_not_validate=True)

        assert _get_plugin_calls() == 1

        assert not mock_validation.called

    def test_can_validate_called_on_update_sync(self, mock_validation, resource_factory):
        """Plugin must be called 2 times for SYNC mode.
        1. resource before_create on resource create
        2. resource before_update on resource update
        """
        resource = resource_factory()

        assert _get_plugin_calls() == 1

        resource['format'] = 'CSV'
        resource['url'] = 'https://example.com/data.csv'

        helpers.call_action('resource_update', **resource)

        assert mock_validation.called
        assert _get_plugin_calls() == 2

    def test_can_validate_called_on_update_sync_no_validation(
            self, mock_validation, resource_factory):
        """Plugin must be called 2 times for SYNC mode.
        1. resource before_create on resource create
        2. resource before_update on resource update
        """
        resource = resource_factory(do_not_validate=True)
        assert _get_plugin_calls() == 1

        resource['format'] = 'TTF'
        helpers.call_action('resource_update', **resource)

        assert _get_plugin_calls() == 2
        assert not mock_validation.called


@pytest.mark.usefixtures("clean_db", "validation_setup")
@pytest.mark.ckan_config(settings.CREATE_MODE, settings.ASYNC_MODE)
@pytest.mark.ckan_config(settings.UPDATE_MODE, settings.ASYNC_MODE)
@mock.patch(validation_helpers.MOCK_ENQUEUE_JOB)
class TestInterfaceAsync(BaseTestInterfaces):

    def test_can_validate_called_on_create_async(self, mock_validation,
                                                 resource_factory):
        """Plugin must be called once for ASYNC mode on create
        1. resource after_create
        """
        resource_factory()

        assert _get_plugin_calls() == 1

        assert mock_validation.called

    def test_can_validate_called_on_create_async_no_validation(
            self, mock_validation, resource_factory):
        """Plugin must be called once for ASYNC mode on create
        1. resource after_create
        """
        resource_factory(do_not_validate=True)

        assert _get_plugin_calls() == 1

        assert not mock_validation.called

    def test_can_validate_called_on_update_async(self, mock_validation,
                                                 resource_factory):
        """Plugin must be called 3 times for ASYNC mode.
        1. resource after_create on resource create
        2. resource before_update on resource update
        3. resource after_update on resource update
        """
        resource = resource_factory(format="PDF")

        assert _get_plugin_calls() == 1

        resource['format'] = 'CSV'

        helpers.call_action('resource_update', **resource)

        assert _get_plugin_calls() == 3
        assert mock_validation.called

    def test_can_validate_called_on_update_async_no_validation(
            self, mock_validation, resource_factory):
        """Plugin must be called 2 times for ASYNC mode.
        1. resource after_create on resource create
        2. resource before_update on resource update
        3. after_update won't be called, because validation is not required (
            format is not supported
        )
        """
        resource = resource_factory(format="PDF")

        assert _get_plugin_calls() == 1

        resource['format'] = "TTF"
        helpers.call_action('resource_update', **resource)

        assert _get_plugin_calls() == 2
        assert not mock_validation.called
