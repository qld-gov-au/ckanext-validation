from ckan.tests.helpers import change_config

from ckanext.validation.utils import (get_create_mode, get_update_mode)


class TestConfig(object):

    def test_config_defaults(self):

        assert get_update_mode() == 'async'
        assert get_create_mode() == 'async'

    @change_config('ckanext.validation.run_on_update_sync', True)
    def test_config_update_true_sync(self):

        assert get_update_mode() == 'sync'

    @change_config('ckanext.validation.run_on_update_sync', False)
    def test_config_update_false_sync(self):

        assert get_update_mode() == 'async'

    @change_config('ckanext.validation.run_on_create_sync', True)
    def test_config_create_true_sync(self):

        assert get_create_mode() == 'sync'

    @change_config('ckanext.validation.run_on_create_sync', False)
    def test_config_create_false_sync(self):

        assert get_create_mode() == 'async'

    @change_config('ckanext.validation.run_on_update_async', True)
    def test_config_update_true_async(self):

        assert get_update_mode() == 'async'

    @change_config('ckanext.validation.run_on_update_async', False)
    def test_config_update_false_async(self):

        assert get_update_mode() is None

    @change_config('ckanext.validation.run_on_create_async', True)
    def test_config_create_true_async(self):

        assert get_create_mode() == 'async'

    @change_config('ckanext.validation.run_on_create_async', False)
    def test_config_create_false_async(self):

        assert get_create_mode() is None

    @change_config('ckanext.validation.run_on_update_async', False)
    @change_config('ckanext.validation.run_on_create_async', False)
    def test_config_both_false(self):

        assert get_update_mode() is None
        assert get_create_mode() is None
