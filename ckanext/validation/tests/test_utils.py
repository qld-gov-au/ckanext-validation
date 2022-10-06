import pytest

from ckan.tests.helpers import change_config

from ckanext.validation import settings
from ckanext.validation.utils import (
    get_create_mode,
    get_update_mode,
    get_supported_formats,
)


class TestConfigValidationMode(object):

    def test_config_defaults(self):

        assert get_update_mode({}, {}) == settings.SYNC_MODE
        assert get_create_mode({}, {}) == settings.SYNC_MODE

    @change_config(settings.ASYNC_CREATE_KEY, True)
    def test_set_async_as_default_create_mode(self):

        assert get_create_mode({}, {}) == settings.ASYNC_MODE

    @change_config(settings.ASYNC_UPDATE_KEY, True)
    def test_set_async_as_default_update_mode(self):

        assert get_update_mode({}, {}) == settings.ASYNC_MODE

    @change_config(settings.ASYNC_CREATE_KEY, False)
    def test_set_sync_as_default_create_mode(self):

        assert get_create_mode({}, {}) == settings.SYNC_MODE

    @change_config(settings.ASYNC_UPDATE_KEY, False)
    def test_set_sync_as_default_update_mode(self):

        assert get_update_mode({}, {}) == settings.SYNC_MODE

    @change_config(settings.ASYNC_CREATE_KEY, False)
    @change_config(settings.ASYNC_UPDATE_KEY, False)
    def test_set_sync_as_default_both_create_and_update(self):

        assert get_create_mode({}, {}) == settings.SYNC_MODE
        assert get_update_mode({}, {}) == settings.SYNC_MODE


class TestConfigSupportedFormats(object):

    def test_default_supported_formats(self):
        assert settings.DEFAULT_SUPPORTED_FORMATS == get_supported_formats()

    @change_config(settings.SUPPORTED_FORMATS_KEY, "")
    def test_empty_supported_formats(self):
        assert settings.DEFAULT_SUPPORTED_FORMATS == get_supported_formats()

    @change_config(settings.SUPPORTED_FORMATS_KEY, "ttf")
    def test_set_unsupported_format(self):
        with pytest.raises(AssertionError, match="Format ttf is not supported"):
            get_supported_formats()

    @change_config(settings.SUPPORTED_FORMATS_KEY, "csv xlsx")
    def test_set_supported_formats(self):
        assert get_supported_formats() == ["csv", "xlsx"]
