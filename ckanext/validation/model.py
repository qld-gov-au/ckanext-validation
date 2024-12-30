# encoding: utf-8
import datetime
import logging

import sqlalchemy
from sqlalchemy import create_engine, Column, Unicode, DateTime
from sqlalchemy.dialects.postgresql import JSON

import ckantoolkit as t
from ckan import model
from ckan.model import types as _types
from ckan.model.meta import metadata

try:
    from ckan.plugins.toolkit import BaseModel as Base
except ImportError:
    # CKAN <= 2.9
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base(metadata=metadata)

log = logging.getLogger(__name__)


class Validation(Base):
    __tablename__ = u'validation'

    id = Column('id', Unicode, primary_key=True, default=_types.make_uuid)
    resource_id = Column('resource_id', Unicode, nullable=False)
    #  status can be one of these values:
    #     created: Job created and put onto queue
    #     running: Job picked up by worker and being processed
    #     success: Validation Successful and report attached
    #     failure: Validation Failed and report attached
    #     error: Validation Job could not create validation report
    status = Column('status', Unicode, default=u'created', nullable=False)
    # created is when job was added
    created = Column('created', DateTime, default=datetime.datetime.utcnow, nullable=False)
    # finished is when report was generated, is None when new or restarted
    finished = Column('finished', DateTime, nullable=True)
    # json object of report, can be None
    report = Column('report', JSON, nullable=True)
    # json object of error, can be None
    error = Column('error', JSON, nullable=True)


def create_tables():
    # metadata.create_all(model.meta.engine) #  This creates all tables, not just our plugin
    Validation.__table__.create(bind=model.meta.engine, checkfirst=True)  # Only creates this table

    log.info(u'Validation database tables created')


# Check the version of SQLAlchemy manually
def is_sqlalchemy_14_or_newer():
    return sqlalchemy.__version__.startswith('1.4') or sqlalchemy.__version__.startswith('2.')


def tables_exist():
    if is_sqlalchemy_14_or_newer():
        from sqlalchemy import inspect
        if model.meta.engine is None:
            # Unsure why this is None when it should be set at this stage.
            log.info("Database engine is not initialized. Going direct")
            engine = create_engine(t.config.get("sqlalchemy.url"))
        else:
            engine = model.meta.engine
        inspector = inspect(engine)
        return 'validation' in inspector.get_table_names()
    else:
        return Validation.__table__.exists()
