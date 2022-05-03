import logging

from flask import Blueprint

import ckanext.validation.common as common

log = logging.getLogger(__name__)
validation = Blueprint(u'validation', __name__)


def read(id, resource_id):
    return common.validation(resource_id)


validation.add_url_rule(u'/dataset/<id>/resource/<resource_id>/validation', view_func=read)


def get_blueprints():
    return [validation]
