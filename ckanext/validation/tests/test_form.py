import json
import io
import mock
import datetime

import pytest
import six

import ckantoolkit as t
from ckantoolkit.tests.factories import Sysadmin, Dataset
from ckantoolkit.tests.helpers import (
    call_action, _get_test_app
)

from ckanext.validation.tests.helpers import VALID_CSV, INVALID_CSV, mock_uploads

is_ckan29_or_higher = t.check_ckan_version(min_version="2.9")


def _post(app, url, extra_environ=None, data=None, upload=None):
    ''' Submit a POST request to 'app',
    using either webtest or Flask syntax.
    '''
    if is_ckan29_or_higher:
        if upload:
            for entry in upload:
                data[entry[0]] = (io.BytesIO(entry[2]), entry[1])
        app.post(
            url=url, extra_environ=extra_environ, data=data)
    else:
        app.post(
            url, data, extra_environ=extra_environ, upload_files=upload)


def _new_resource_url(dataset_id):

    if is_ckan29_or_higher:
        url = "/dataset/{}/resource/new".format(dataset_id)
    else:
        url = "/dataset/new_resource/{}".format(dataset_id)
    return url


def _edit_resource_url(dataset_id, resource_id):

    if is_ckan29_or_higher:
        url = "/dataset/{}/resource/{}/edit".format(dataset_id, resource_id)
    else:
        url = "/dataset/{}/resource_edit/{}".format(dataset_id, resource_id)
    return url


def _get_resource_new_page_as_sysadmin(app, id):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(
        url="/dataset/new_resource/{}".format(id),
        extra_environ=env,
    )
    return env, response


def _get_resource_update_page_as_sysadmin(app, id, resource_id):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(
        url="/dataset/{}/resource_edit/{}".format(id, resource_id),
        extra_environ=env,
    )
    return env, response


@pytest.mark.usefixtures("clean_db", "validation_setup", "with_plugins")
class TestResourceSchemaForm(object):
    def test_resource_form_includes_json_fields(self, app):
        dataset = Dataset()
        env, response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        assert '<input type="hidden" id="field-schema" name="schema"' in response.body
        assert '<input id="field-schema-url" type="url" name="schema_url"' in response.body
        assert '<textarea id="field-schema-json" name="schema_json"' in response.body

    def test_resource_form_create(self, app):
        dataset = Dataset()

        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        json_value = json.dumps(value)

        data = {
            "url": "https://example.com/data.csv",
            "schema": json_value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_new_resource_url(dataset['id']),
            extra_environ=env,
            data=data,
        )
        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_create_json(self, app):
        dataset = Dataset()

        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        json_value = json.dumps(value)

        data = {
            "url": "https://example.com/data.csv",
            "schema_json": json_value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_new_resource_url(dataset['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_create_upload(self):
        dataset = Dataset()

        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        json_value = six.ensure_binary(json.dumps(value).encode('utf8'))

        data = {
            "url": "https://example.com/data.csv",
            "id": "",
            "save": "",
        }

        upload = ('schema_upload', 'schema.json', json_value)

        app = _get_test_app()

        @mock_uploads
        def post(app, data, mock_open):

            user = Sysadmin()
            env = {"REMOTE_USER": user["name"].encode("ascii")}

            _post(
                app,
                url=_new_resource_url(dataset['id']),
                extra_environ=env,
                data=data,
                upload=[upload]
            )
        post(app, data)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_create_url(self, app):
        dataset = Dataset()

        value = "https://example.com/schemas.json"
        data = {
            "url": "https://example.com/data.csv",
            "schema_url": value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_new_resource_url(dataset['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_update(self, app):
        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        dataset = Dataset(
            resources=[{"url": "https://example.com/data.csv", "schema": value}]
        )

        value = {"fields": [{"name": "code"}, {"name": "department"}, {"name": "date"}]}

        json_value = json.dumps(value)

        data = {
            "url": "https://example.com/data.csv",
            # Clear current value
            "schema_json": "",
            "schema": json_value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_edit_resource_url(dataset['id'], dataset['resources'][0]['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_update_json(self, app):
        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        dataset = Dataset(
            resources=[{"url": "https://example.com/data.csv", "schema": value}]
        )

        value = {"fields": [{"name": "code"}, {"name": "department"}, {"name": "date"}]}

        json_value = json.dumps(value)
        data = {
            "url": "https://example.com/data.csv",
            "schema_json": json_value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_edit_resource_url(dataset['id'], dataset['resources'][0]['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_update_url(self, app):
        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        dataset = Dataset(
            resources=[{"url": "https://example.com/data.csv", "schema": value}]
        )

        value = "https://example.com/schema.json"

        data = {
            "url": "https://example.com/data.csv",
            "schema_url": value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_edit_resource_url(dataset['id'], dataset['resources'][0]['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value

    def test_resource_form_update_upload(self, app):
        value = {"fields": [{"name": "code"}, {"name": "department"}]}
        dataset = Dataset(
            resources=[{"url": "https://example.com/data.csv", "schema": value}]
        )

        value = {"fields": [{"name": "code"}, {"name": "department"}, {"name": "date"}]}
        json_value = six.ensure_binary(json.dumps(value).encode('utf8'))

        upload = ('schema_upload', 'schema.json', json_value)

        data = {
            "url": "https://example.com/data.csv",
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_edit_resource_url(dataset['id'], dataset['resources'][0]['id']),
            extra_environ=env,
            data=data,
            upload=[upload],
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == value


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOptionsForm(object):
    def test_resource_form_includes_json_fields(self, app):
        dataset = Dataset()

        env, response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        assert '<textarea id="field-validation_options" name="validation_options"' in response.body

    def test_resource_form_create(self, app):
        dataset = Dataset()

        value = {
            "delimiter": ";",
            "headers": 2,
            "skip_rows": ["#"],
        }
        json_value = json.dumps(value)
        data = {
            "url": "https://example.com/data.csv",
            "validation_options": json_value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_new_resource_url(dataset['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["validation_options"] == value

    def test_resource_form_update(self, app):
        value = {
            "delimiter": ";",
            "headers": 2,
            "skip_rows": ["#"],
        }

        dataset = Dataset(
            resources=[
                {"url": "https://example.com/data.csv", "validation_options": value}
            ]
        )

        value = {
            "delimiter": ";",
            "headers": 2,
            "skip_rows": ["#"],
            "skip_tests": ["blank-rows"],
        }

        json_value = json.dumps(value)
        data = {
            "url": "https://example.com/data.csv",
            "validation_options": json_value,
            "id": "",
            "save": "",
        }

        user = Sysadmin()
        env = {"REMOTE_USER": user["name"].encode("ascii")}

        _post(
            app,
            url=_edit_resource_url(dataset['id'], dataset['resources'][0]['id']),
            extra_environ=env,
            data=data,
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["validation_options"] == value


@pytest.mark.usefixtures("clean_db", "validation_setup")
@pytest.mark.skip(reason="Need to update this for py3")
class TestResourceValidationOnCreateForm(object):
    @classmethod
    def setup_class(cls):
        # Needed to apply the config changes at the right time so they can be picked up
        # during startup
        cls._original_config = dict(t.config)
        t.config["ckanext.validation.run_on_create_sync"] = True

    @classmethod
    def teardown_class(cls):

        t.config.clear()
        t.config.update(cls._original_config)

    @mock_uploads
    def test_resource_form_create_valid(self, mock_open, app):

        raise pytest.Skip

        dataset = Dataset()

        env, response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        response.forms["resource-edit"]

        ("upload", "valid.csv", VALID_CSV)

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        with mock.patch("io.open", return_value=valid_stream):
            pass

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["validation_status"] == "success"
        assert "validation_timestamp" in dataset["resources"][0]

    @mock_uploads
    def test_resource_form_create_invalid(self, mock_open, app):
        dataset = Dataset()

        env, response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        response.forms["resource-edit"]

        ("upload", "invalid.csv", INVALID_CSV)

        invalid_stream = io.BufferedReader(io.BytesIO(INVALID_CSV))

        with mock.patch("io.open", return_value=invalid_stream):
            pass

        assert "validation" in response.body
        assert "missing-value" in response.body
        assert "Row 2 has a missing value in column 4" in response.body


@pytest.mark.usefixtures("clean_db", "validation_setup")
@pytest.mark.skip(reason="Need to update this for py3")
class TestResourceValidationOnUpdateForm(object):
    @classmethod
    def setup_class(cls):
        # Needed to apply the config changes at the right time so they can be picked up
        # during startup
        cls._original_config = dict(t.config)
        t.config["ckanext.validation.run_on_update_sync"] = True

    @classmethod
    def teardown_class(cls):

        t.config.clear()
        t.config.update(cls._original_config)

    @mock_uploads
    def test_resource_form_update_valid(self, mock_open, app):

        dataset = Dataset(resources=[{"url": "https://example.com/data.csv"}])

        env, response = _get_resource_update_page_as_sysadmin(
            app, dataset["id"], dataset["resources"][0]["id"]
        )
        response.forms["resource-edit"]

        ("upload", "valid.csv", VALID_CSV)

        valid_stream = io.BufferedReader(io.BytesIO(VALID_CSV))

        with mock.patch("io.open", return_value=valid_stream):
            pass

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["validation_status"] == "success"
        assert "validation_timestamp" in dataset["resources"][0]

    @mock_uploads
    def test_resource_form_update_invalid(self, mock_open, app):

        dataset = Dataset(resources=[{"url": "https://example.com/data.csv"}])

        env, response = _get_resource_update_page_as_sysadmin(
            app, dataset["id"], dataset["resources"][0]["id"]
        )
        response.forms["resource-edit"]

        ("upload", "invalid.csv", INVALID_CSV)

        invalid_stream = io.BufferedReader(io.BytesIO(INVALID_CSV))

        with mock.patch("io.open", return_value=invalid_stream):
            pass

        assert "validation" in response.body
        assert "missing-value" in response.body
        assert "Row 2 has a missing value in column 4" in response.body


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationFieldsPersisted(object):
    @classmethod
    def setup_class(cls):
        # Needed to apply the config changes at the right time so they can be picked up
        # during startup
        cls._original_config = dict(t.config)
        t.config["ckanext.validation.run_on_update_sync"] = False

    @classmethod
    def teardown_class(cls):

        t.config.clear()
        t.config.update(cls._original_config)

    def test_resource_form_fields_are_persisted(self, app):

        dataset = Dataset(
            resources=[
                {
                    "url": "https://example.com/data.csv",
                    "validation_status": "success",
                    "validation_timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        )

        env, response = _get_resource_update_page_as_sysadmin(
            app, dataset["id"], dataset["resources"][0]["id"]
        )

        assert '<input type="hidden" name="validation_status" value="success"' in response.body
        assert '<input type="hidden" name="validation_timestamp"' in response.body
