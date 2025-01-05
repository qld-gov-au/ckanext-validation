# encoding: utf-8

import datetime
import uuid
import logging

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from six import text_type

from ckan import model
from ckan.model.meta import mapper, metadata

log = logging.getLogger(__name__)


def make_uuid():
    return text_type(uuid.uuid4())


class Validation(model.DomainObject):
    @classmethod
    def get(cls, **kw):
        '''Finds all the instances required.'''
        query = model.Session.query(cls).autoflush(False)
        return query.filter_by(**kw).all()


validation_table = sa.Table('validation', metadata,
                            sa.Column('id', sa.types.UnicodeText, primary_key=True, default=make_uuid),
                            sa.Column('resource_id', sa.types.UnicodeText, primary_key=False),
                            sa.Column('status', sa.types.UnicodeText, primary_key=False, default='created'),
                            sa.Column('created', sa.types.DateTime, primary_key=False, default=datetime.datetime.utcnow),
                            sa.Column('finished', sa.types.DateTime, primary_key=False),
                            sa.Column('report', JSON, primary_key=False),
                            sa.Column('error', JSON, primary_key=False)
                            )

mapper(Validation, validation_table)


def create_tables():
    metadata.create_all(model.meta.engine)

    log.info(u'Validation database tables created')
