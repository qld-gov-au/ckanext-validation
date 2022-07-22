# encoding: utf-8

from flask import Blueprint

from ckanext.validation import common

validation = Blueprint(u'validation', __name__)


def read(id, resource_id):
    return common.validation(resource_id)


validation.add_url_rule(u'/dataset/<id>/resource/<resource_id>/validation', view_func=read)


def get_blueprints():
    return [validation]
