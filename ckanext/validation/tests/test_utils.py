import pytest

from ckan.tests.helpers import change_config

from ckanext.validation import settings as s


class TestConfigValidationMode(object):

    def test_config_defaults(self):

        assert s.get_update_mode({}, {}) == s.SYNC_MODE
        assert s.get_create_mode({}, {}) == s.SYNC_MODE

    @change_config(s.ASYNC_CREATE_KEY, True)
    def test_set_async_as_default_create_mode(self):

        assert s.get_create_mode({}, {}) == s.ASYNC_MODE

    @change_config(s.ASYNC_UPDATE_KEY, True)
    def test_set_async_as_default_update_mode(self):

        assert s.get_update_mode({}, {}) == s.ASYNC_MODE

    @change_config(s.ASYNC_CREATE_KEY, False)
    def test_set_sync_as_default_create_mode(self):

        assert s.get_create_mode({}, {}) == s.SYNC_MODE

    @change_config(s.ASYNC_UPDATE_KEY, False)
    def test_set_sync_as_default_update_mode(self):

        assert s.get_update_mode({}, {}) == s.SYNC_MODE

    @change_config(s.ASYNC_CREATE_KEY, False)
    @change_config(s.ASYNC_UPDATE_KEY, False)
    def test_set_sync_as_default_both_create_and_update(self):

        assert s.get_create_mode({}, {}) == s.SYNC_MODE
        assert s.get_update_mode({}, {}) == s.SYNC_MODE


class TestConfigSupportedFormats(object):

    def test_default_supported_formats(self):
        assert s.DEFAULT_SUPPORTED_FORMATS == s.get_supported_formats()

    @change_config(s.SUPPORTED_FORMATS_KEY, "")
    def test_empty_supported_formats(self):
        assert s.DEFAULT_SUPPORTED_FORMATS == s.get_supported_formats()

    @change_config(s.SUPPORTED_FORMATS_KEY, "ttf")
    def test_set_unsupported_format(self):
        with pytest.raises(AssertionError, match="Format ttf is not supported"):
            s.get_supported_formats()

    @change_config(s.SUPPORTED_FORMATS_KEY, "csv xlsx")
    def test_set_supported_formats(self):
        assert s.get_supported_formats() == ["csv", "xlsx"]
