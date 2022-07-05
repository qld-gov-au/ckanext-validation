import pytest

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
