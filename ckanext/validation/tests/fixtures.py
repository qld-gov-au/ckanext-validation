import json

import pytest
import factory
import responses
import six
from pytest_factoryboy import register

import ckan.plugins.toolkit as tk
from ckan.lib import uploader
from ckan.tests import factories

from ckanext.validation.model import create_tables, tables_exist
from ckanext.validation.tests.helpers import VALID_CSV, MockFieldStorage, SCHEMA


@pytest.fixture
def validation_setup(monkeypatch, ckan_config, tmpdir):
    monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
    monkeypatch.setattr(uploader, u'_storage_path', str(tmpdir))

    if not tables_exist():
        create_tables()


@pytest.fixture
def org():
    return factories.Organization()


@pytest.fixture
def dataset(org):
    return factories.Dataset(private=True, owner_org=org['id'])


@pytest.fixture
def mocked_responses():
    solr_url = tk.config.get('solr_url', 'http://127.0.0.1:8983/solr/ckan')

    with responses.RequestsMock() as rsps:
        rsps.add_passthru(solr_url)
        yield rsps


class ResourceFactory(factories.Resource):
    id = factory.Faker("uuid4")
    description = factory.Faker("sentence")
    schema = factory.LazyFunction(lambda: json.dumps(SCHEMA))
    format = "CSV"
    url = None
    url_type = "upload"
    upload = factory.LazyFunction(
        lambda: MockFieldStorage(six.BytesIO(VALID_CSV), 'data.csv'))

register(ResourceFactory, "resource")
