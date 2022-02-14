# encoding: utf-8

from flask import Blueprint

from . import validation_report


validation = Blueprint(
    u'validation',
    __name__
)

validation.add_url_rule(
    u'/dataset/<id>/resource/<resource_id>/validation' 'qa_resource_checklink', methods=('GET',), view_func=validation_report
)


def get_blueprints():
    return [validation]
