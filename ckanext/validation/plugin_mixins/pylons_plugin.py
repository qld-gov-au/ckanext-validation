# encoding: utf-8

import ckan.plugins as p


class MixinPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # IRoutes

    def before_map(self, map_):

        controller = u'ckanext.validation.controller:ValidationController'

        map_.connect(
            u'validation_read',
            u'/dataset/{id}/resource/{resource_id}/validation',
            controller=controller, action=u'validation')

        return map_
