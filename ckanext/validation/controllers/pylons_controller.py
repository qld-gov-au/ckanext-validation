# encoding: utf-8

from ckantoolkit import BaseController

from . import validation_report


class ValidationController(BaseController):

    def validation(self, resource_id):
        return validation_report(resource_id)
