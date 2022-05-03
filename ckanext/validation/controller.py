# encoding: utf-8

import ckanext.validation.common as common


class ValidationController(BaseController):

    def validation(self, resource_id):
        return common.validation(resource_id)
