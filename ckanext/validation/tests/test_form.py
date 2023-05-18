# encoding: utf-8

import json
import mock
import pytest

from bs4 import BeautifulSoup

from ckan.tests.factories import Sysadmin, Dataset
from ckan.tests.helpers import call_action

from ckanext.validation.tests.helpers import (
    NEW_SCHEMA,
    VALID_CSV,
    INVALID_CSV,
    SCHEMA,
    VALID_REPORT,
    get_mock_upload,
)

NEW_RESOURCE_URL = "/dataset/{}/resource/new"
EDIT_RESOURCE_URL = "/dataset/{}/resource/{}/edit"


def _get_resource_new_page_as_sysadmin(app, id):
    """Returns a resource create page response"""
    response = app.get(
        url=NEW_RESOURCE_URL.format(id),
        extra_environ=_get_sysadmin_env(),
    )
    return response


def _get_resource_update_page_as_sysadmin(app, id, resource_id):
    """Returns a resource update page response"""
    response = app.get(
        url=EDIT_RESOURCE_URL.format(id, resource_id),
        extra_environ=_get_sysadmin_env(),
    )
    return response


def _get_sysadmin_env():
    user = Sysadmin()
    return {"REMOTE_USER": user["name"].encode("ascii")}


def _get_form(response):
    soup = BeautifulSoup(response.body, "html.parser")
    return soup.find("form", id="resource-edit")


def _post(app, url, data):
    data["save"] = ""
    data.setdefault("id", "")
    return app.post(url=url, data=data, extra_environ=_get_sysadmin_env())


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceSchemaForm(object):

    def test_resource_form_includes_schema_fields(self, app):
        """All schema related fields must be in the resource form"""
        dataset = Dataset()

        response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        form = _get_form(response)

        assert form.find("input", attrs={"name": "schema"})
        assert form.find("input", attrs={"name": "schema_upload"})
        assert form.find("textarea", attrs={"name": "schema_json"})
        assert form.find("input", attrs={"name": "schema_url"})

    def test_resource_form_create_with_schema(self, app):
        """Test we are able to create a resource with a schema"""
        dataset = Dataset()

        data = {
            "name": "test_resource_form_create",
            "schema": json.dumps(SCHEMA),
        }

        _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == SCHEMA

    def test_resource_form_create_schema_from_schema_json(self, app):
        """Test we are able to create a resource with schema from a json"""
        dataset = Dataset()

        data = {
            "name": "test_resource_form_create_json",
            "url": "https://example.com/data.csv",
            "schema_json": json.dumps(SCHEMA),
        }

        _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == SCHEMA

    def test_resource_form_create_schema_from_schema_upload(self, app):
        """Test we are able to create a resource with schema from an uploaded file"""
        dataset = Dataset()

        data = {
            "name": "test_resource_form_create_upload",
            "url": "https://example.com/data.csv",
            "schema_upload": get_mock_upload(SCHEMA, "schema.json"),
        }

        _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == SCHEMA

    def test_resource_form_create_schema_from_schema_url(
            self, app, mocked_responses):
        """Test we are able to create a resource with schema from a url"""
        dataset = Dataset()

        value = "https://example.com/schemas.json"
        mocked_responses.add("GET", value, json=SCHEMA)

        data = {
            "name": "test_resource_form_create_url",
            "package_id": dataset["id"],
            "url": "https://example.com/data.csv",
            "schema_url": value,
        }

        _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schema"] == SCHEMA

    def test_resource_form_update_with_new_schema(self, app, resource_factory):
        """Test we are able to update a resource with a new schema"""
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"])
        resource_id = resource["id"]

        assert resource["schema"] == SCHEMA

        data = {
            "name": "test_resource_form_update",
            "url": "https://example.com/data.csv",
            "schema": json.dumps(NEW_SCHEMA)
        }

        _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource_id),
            data=data
        )

        resource = call_action("resource_show", id=resource_id)

        assert resource["schema"] == NEW_SCHEMA

    def test_resource_form_update_json(self, app, resource_factory):
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"])
        resource_id = resource["id"]

        assert resource["schema"] == SCHEMA

        data = {
            "schema_json": json.dumps(NEW_SCHEMA)
        }

        _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource_id),
            data=data
        )

        resource = call_action("resource_show", id=resource_id)

        assert resource["schema"] == NEW_SCHEMA

    def test_resource_form_update_url(self, app, resource_factory,
                                      mocked_responses):
        """Test we are able to replace a schema from a url to an existing resource"""
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"])
        resource_id = resource["id"]

        assert resource["schema"] == SCHEMA

        schema_url = "https://example.com/schema.json"
        mocked_responses.add("GET", schema_url, json=NEW_SCHEMA)
        data = {
            "schema_url": schema_url
        }

        _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource_id),
            data=data
        )

        resource = call_action("resource_show", id=resource_id)

        assert resource["schema"] == NEW_SCHEMA

    def test_resource_form_update_upload(self, app, resource_factory):
        """Test we are able to replace a schema from a file for an existing resource"""
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"])
        resource_id = resource["id"]

        assert resource["schema"] == SCHEMA

        data = {
            "schema_upload": get_mock_upload(NEW_SCHEMA, "schema.json"),
        }

        _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource_id),
            data=data
        )

        resource = call_action("resource_show", id=resource["id"])

        assert resource["schema"] == NEW_SCHEMA


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOptionsForm(object):

    def test_resource_form_includes_validation_options_field(self, app):
        """validation_options must be in the resource form"""
        dataset = Dataset()

        response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        form = _get_form(response)

        assert form.find("textarea", attrs={"name": "validation_options"})

    def test_resource_form_create(self, app):
        dataset = Dataset()

        value = {
            "delimiter": ",",
            "headers": 1,
        }
        json_value = json.dumps(value)
        data = {
            "name": "test_resource_form_create",
            "url": "https://example.com/data.csv",
            "validation_options": json_value,
        }

        _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["validation_options"] == value

    def test_resource_form_update(self, app, resource_factory):
        value = {
            "delimiter": ",",
            "headers": 1,
            "skip_rows": ["#"],
        }

        resource = resource_factory(validation_options=value)
        resource_id = resource["id"]

        response = _get_resource_update_page_as_sysadmin(
            app, resource["package_id"], resource_id)
        form = _get_form(response)

        assert form.find("textarea",
                         attrs={"name": "validation_options"}).text ==\
            json.dumps(value, indent=2, sort_keys=True)

        value = {
            "delimiter": ",",
            "headers": 4,
            "skip_rows": ["#"],
            "skip_tests": ["blank-rows"],
        }

        data = {
            "name": "test_resource_form_update",
            "url": "https://example.com/data.csv",
            "validation_options": json.dumps(value)
        }

        _post(
            app,
            url=EDIT_RESOURCE_URL.format(resource["package_id"], resource_id),
            data=data
        )
        resource = call_action("resource_show", id=resource["id"])

        assert resource["validation_options"] == value


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOnCreateForm(object):

    def test_resource_form_create_valid(self, app):
        """Test we are able to create resource with a valid CSV file.
        If schema and format is provided - resource will be validated according
        to the schema"""
        dataset = Dataset()

        data = {
            "name": "test_resource_form_create_valid",
            "url": "https://example.com/data.csv",
            "schema": json.dumps(SCHEMA),
            "format": "csv",
            "upload": get_mock_upload(VALID_CSV, "valid.csv"),
        }

        _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["validation_status"] == "success"
        assert "validation_timestamp" in dataset["resources"][0]

    def test_resource_form_create_invalid(self, app):
        """Test we aren't able to create resource with an invalid CSV file.
        If schema and format is provided - resource will be validated according
        to the schema.
        """
        dataset = Dataset()

        data = {
            "name": "test_resource_form_create_invalid",
            "url": "https://example.com/data.csv",
            "schema": json.dumps(SCHEMA),
            "format": "csv",
            "upload": get_mock_upload(INVALID_CSV, "invalid.csv"),
        }

        response = _post(
            app,
            url=NEW_RESOURCE_URL.format(dataset["id"]),
            data=data
        )

        assert "validation" in response.body
        assert "missing-value" in response.body
        assert "Row 2 has a missing value in column 4" in response.body


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationOnUpdateForm(object):

    def test_resource_form_update_valid(self, app, resource_factory):
        """Test we are able to update resource with a valid CSV file.
        If schema and format is provided - resource will be validated according
        to the schema"""
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"], format="PDF")
        resource_id = resource["id"]

        data = {
            "name": "test_resource_form_update_valid",
            "url": "https://example.com/data.csv",
            "format": "csv",
            "schema": json.dumps(SCHEMA),
            "upload": get_mock_upload(VALID_CSV, "valid.csv"),
        }

        response = _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource_id),
            data=data
        )

        assert "missing-value" not in response.body
        assert "Row 2 has a missing value in column 4" not in response.body

        resource = call_action("resource_show", id=resource_id)

        assert resource["validation_status"] == "success"
        assert resource["validation_timestamp"]

    def test_resource_form_update_invalid(self, app, resource_factory):
        """Test we aren't able to update resource with an invalid CSV file.
        If schema and format is provided - resource will be validated according
        to the schema"""
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"])

        data = {
            "format": "csv",
            "schema": json.dumps(SCHEMA),
            "upload": get_mock_upload(INVALID_CSV, "invalid.csv"),
        }
        response = _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource["id"]),
            data=data
        )

        assert "validation" in response.body
        assert "missing-value" in response.body
        assert "Row 2 has a missing value in column 4" in response.body


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestResourceValidationFieldsPersisted(object):

    @mock.patch("ckanext.validation.utils.validate", return_value=VALID_REPORT)
    def test_resource_form_fields_are_persisted(self, mock_report, app,
                                                resource_factory):
        dataset = Dataset()
        resource = resource_factory(package_id=dataset["id"], description="")

        assert resource["validation_status"] == "success"
        assert not resource.get("description")

        data = {
            "description": "test desc",
            "url": "https://example.com/data.xlsx",
            "format": "xlsx",
            "schema": json.dumps(SCHEMA),
        }

        _post(
            app,
            url=EDIT_RESOURCE_URL.format(dataset["id"], resource["id"]),
            data=data
        )

        resource = call_action("resource_show", id=resource["id"])

        assert resource["validation_timestamp"]
        assert resource["validation_status"] == "success"
        assert resource["description"] == "test desc"
