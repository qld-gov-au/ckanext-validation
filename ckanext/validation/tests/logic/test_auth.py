# encoding: utf-8

import pytest

from ckan import model
from ckan.tests.helpers import call_auth
from ckan.tests import factories

import ckantoolkit as tk


@pytest.mark.usefixtures("clean_db", "validation_setup")
class TestAuth(object):

    def test_run_anon(self):

        resource = factories.Resource()

        context = {'user': None, 'model': model}

        with pytest.raises(tk.NotAuthorized):
            call_auth('resource_validation_run',
                      context=context,
                      resource_id=resource['id'])

    def test_run_sysadmin(self):
        resource = factories.Resource()
        sysadmin = factories.Sysadmin()

        context = {'user': sysadmin['name'], 'model': model}

        assert call_auth('resource_validation_run',
                         context=context,
                         resource_id=resource['id'])

    def test_run_non_auth_user(self):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()])

        context = {'user': user['name'], 'model': model}

        with pytest.raises(tk.NotAuthorized):
            call_auth('resource_validation_run',
                      context=context,
                      resource_id=dataset['resources'][0]['id'])

    def test_run_auth_user(self):
        user = factories.User()
        org = factories.Organization(users=[{
            'name': user['name'],
            'capacity': 'editor'
        }])
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()])

        context = {'user': user['name'], 'model': model}

        assert call_auth('resource_validation_run',
                         context=context,
                         resource_id=dataset['resources'][0]['id'])

    def test_delete_anon(self):
        resource = factories.Resource()

        context = {'user': None, 'model': model}

        with pytest.raises(tk.NotAuthorized):
            call_auth('resource_validation_delete',
                      context=context,
                      resource_id=resource['id'])

    def test_delete_sysadmin(self):
        resource = factories.Resource()
        sysadmin = factories.Sysadmin()

        context = {'user': sysadmin['name'], 'model': model}

        assert call_auth('resource_validation_delete',
                         context=context,
                         resource_id=resource['id'])

    def test_delete_non_auth_user(self):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()])

        context = {'user': user['name'], 'model': model}

        with pytest.raises(tk.NotAuthorized):
            call_auth('resource_validation_delete',
                      context=context,
                      resource_id=dataset['resources'][0]['id'])

    def test_delete_auth_user(self):
        user = factories.User()
        org = factories.Organization(users=[{
            'name': user['name'],
            'capacity': 'editor'
        }])
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()])

        context = {'user': user['name'], 'model': model}

        assert call_auth('resource_validation_delete',
                         context=context,
                         resource_id=dataset['resources'][0]['id'])

    def test_show_anon(self):
        resource = factories.Resource()

        context = {'user': None, 'model': model}

        assert call_auth('resource_validation_show',
                         context=context,
                         resource_id=resource['id'])

    def test_show_anon_public_dataset(self):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()],
                                    private=False)

        context = {'user': user['name'], 'model': model}

        assert call_auth('resource_validation_show',
                         context=context,
                         resource_id=dataset['resources'][0]['id'])

    def test_show_anon_private_dataset(self):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()],
                                    private=True)

        context = {'user': user['name'], 'model': model}

        with pytest.raises(tk.NotAuthorized):
            call_auth('resource_validation_run',
                      context=context,
                      resource_id=dataset['resources'][0]['id'])
