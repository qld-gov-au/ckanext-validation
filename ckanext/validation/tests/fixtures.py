import pytest
import responses

from ckan.tests import factories

from ckanext.validation.model import create_tables, tables_exist


@pytest.fixture
def validation_setup():
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
    from ckan.common import config
    solr_url = config.get('solr_url', 'http://127.0.0.1:8983/solr/ckan')

    with responses.RequestsMock() as rsps:
        rsps.add_passthru(solr_url)
        yield rsps
