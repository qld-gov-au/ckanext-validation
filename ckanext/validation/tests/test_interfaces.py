import mock
from nose.tools import assert_equals, with_setup

from ckan import model, plugins as p
from ckan.tests import helpers, factories

from ckanext.validation.interfaces import IDataValidation
from ckanext.validation.tests.helpers import VALID_REPORT


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


def _setup_function(self):
    helpers.reset_db()
    self.owner_org = factories.Organization(name='test-org')
    self.test_dataset = factories.Dataset(owner_org=self.owner_org['id'])


@with_setup(_setup_function)
class TestPlugin(p.SingletonPlugin):

    p.implements(IDataValidation, inherit=True)

    calls = 0

    def reset_counter(self):
        self.calls = 0

    def can_validate(self, context, data_dict):
        self.calls += 1

        if data_dict.get('my_custom_field') == 'xx':
            return False

        return True


def _get_plugin_calls():
    for plugin in p.PluginImplementations(IDataValidation):
        return plugin.calls


class BaseTestInterfaces():

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('test_validation_plugin'):
            p.load('test_validation_plugin')

    @classmethod
    def teardown_class(cls):
        if p.plugin_loaded('test_validation_plugin'):
            p.unload('test_validation_plugin')

    def setup(self):
        for plugin in p.PluginImplementations(IDataValidation):
            return plugin.reset_counter()


@with_setup(_setup_function)
class TestInterfaceSync(BaseTestInterfaces):

    @mock.patch('ckanext.validation.jobs.validate', return_value=VALID_REPORT)
    def test_can_validate_called_on_create_sync(self, mock_validation):

        helpers.call_action(
            'resource_create',
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id']
        )
        assert_equals(_get_plugin_calls(), 1)

        assert mock_validation.called

    @mock.patch('ckanext.validation.jobs.validate')
    def test_can_validate_called_on_create_sync_no_validation(self, mock_validation):

        helpers.call_action(
            'resource_create',
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id'],
            my_custom_field='xx',
        )
        assert_equals(_get_plugin_calls(), 1)

        assert not mock_validation.called

    @mock.patch('ckanext.validation.jobs.validate', return_value=VALID_REPORT)
    def test_can_validate_called_on_update_sync(self, mock_validation):

        resource = factories.Resource(package_id=self.test_dataset['id'])
        helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id']
        )
        assert_equals(_get_plugin_calls(), 2)  # One for create and one for update

        assert mock_validation.called

    @mock.patch('ckanext.validation.jobs.validate')
    def test_can_validate_called_on_update_sync_no_validation(self, mock_validation):

        resource = factories.Resource(package_id=self.test_dataset['id'])
        helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id'],
            my_custom_field='xx',
        )
        assert_equals(_get_plugin_calls(), 2)  # One for create and one for update

        assert not mock_validation.called


@with_setup(_setup_function)
class TestInterfaceAsync(BaseTestInterfaces):

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    @helpers.change_config('ckanext.validation.run_on_update_sync', False)
    @helpers.change_config('ckanext.validation.run_on_create_async', True)
    @mock.patch('ckantoolkit.enqueue_job')
    def test_can_validate_called_on_create_async(self, mock_validation):

        helpers.call_action(
            'resource_create',
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id']
        )
        assert_equals(_get_plugin_calls(), 1)

        assert mock_validation.called

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    @helpers.change_config('ckanext.validation.run_on_update_sync', False)
    @helpers.change_config('ckanext.validation.run_on_create_async', True)
    @mock.patch('ckantoolkit.enqueue_job')
    def test_can_validate_called_on_create_async_no_validation(self, mock_validation):

        helpers.call_action(
            'resource_create',
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id'],
            my_custom_field='xx',
        )
        assert_equals(_get_plugin_calls(), 1)

        assert not mock_validation.called

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    @helpers.change_config('ckanext.validation.run_on_update_sync', False)
    @helpers.change_config('ckanext.validation.run_on_update_async', True)
    @mock.patch('ckantoolkit.enqueue_job')
    def test_can_validate_called_on_update_async(self, mock_validation):

        resource = factories.Resource(package_id=self.test_dataset['id'])
        helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id']
        )
        assert_equals(_get_plugin_calls(), 1)

        assert mock_validation.called

    @helpers.change_config('ckanext.validation.run_on_create_sync', False)
    @helpers.change_config('ckanext.validation.run_on_update_sync', False)
    @helpers.change_config('ckanext.validation.run_on_update_async', True)
    @mock.patch('ckantoolkit.enqueue_job')
    def test_can_validate_called_on_update_async_no_validation(self, mock_validation):

        resource = factories.Resource(package_id=self.test_dataset['id'])
        helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.com/data.csv',
            format='CSV',
            package_id=self.test_dataset['id'],
            my_custom_field='xx',

        )
        assert_equals(_get_plugin_calls(), 1)

        assert not mock_validation.called
