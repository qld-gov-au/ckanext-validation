# encoding: utf-8

SUPPORTED_FORMATS_KEY = u"ckanext.validation.formats"
DEFAULT_SUPPORTED_FORMATS = [u'csv', u'xls', u'xlsx']
DEFAULT_VALIDATION_OPTIONS_KEY = "ckanext.validation.default_validation_options"

SYNC_MODE = u"sync"
ASYNC_MODE = u"async"
SUPPORTED_MODES = [SYNC_MODE, ASYNC_MODE]

ASYNC_UPDATE_KEY = "ckanext.validation.run_on_update_async"
ASYNC_CREATE_KEY = "ckanext.validation.run_on_create_async"

CREATE_MODE = u"ckanext.validation.default_create_mode"
UPDATE_MODE = u"ckanext.validation.default_update_mode"
DEFAULT_CREATE_MODE = ASYNC_MODE
DEFAULT_UPDATE_MODE = ASYNC_MODE

PASS_AUTH_HEADER = u"ckanext.validation.pass_auth_header"
PASS_AUTH_HEADER_DEFAULT = True

PASS_AUTH_HEADER_VALUE = u"ckanext.validation.pass_auth_header_value"
