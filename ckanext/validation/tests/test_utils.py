import pytest

from ckan.tests.helpers import change_config

import ckanext.validation.settings as settings
from ckanext.validation.utils import get_create_mode, get_update_mode

class TestConfigValidationMode(object):

    def test_config_defaults(self):

        assert get_update_mode({}, {}) == settings.SYNC_MODE
        assert get_create_mode({}, {}) == settings.SYNC_MODE

    @change_config(settings.CREATE_MODE, settings.ASYNC_MODE)
    def test_set_async_as_default_create_mode(self):

        assert get_create_mode({}, {}) == settings.ASYNC_MODE

    @change_config(settings.UPDATE_MODE, settings.ASYNC_MODE)
    def test_set_async_as_default_update_mode(self):

        assert get_update_mode({}, {}) == settings.ASYNC_MODE

    @change_config(settings.CREATE_MODE, settings.SYNC_MODE)
    @change_config(settings.UPDATE_MODE, settings.SYNC_MODE)
    def test_set_sync_as_default_both_create_and_update(self):

        assert get_create_mode({}, {}) == settings.SYNC_MODE
        assert get_update_mode({}, {}) == settings.SYNC_MODE

    @change_config(settings.CREATE_MODE, 'partial')
    def test_set_not_supported_create_mode(self):

        with pytest.raises(AssertionError, match="Mode 'partial' is not supported"):
            assert get_create_mode({}, {}) == settings.SYNC_MODE

    @change_config(settings.UPDATE_MODE, 'partial')
    def test_set_not_supported_update_mode(self):

        with pytest.raises(AssertionError, match="Mode 'partial' is not supported"):
            assert get_update_mode({}, {}) == settings.SYNC_MODE
