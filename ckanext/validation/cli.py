import sys
import click
import pprint

from ckanext.validation.model import create_tables, tables_exist


def get_commands():
    return [validation]


@click.group()
def validation():
    """Validation management commands.
    """
    pass


@validation.command(name='init-db')
def init_db():
    from ckanext.validation.common import init_db
    init_db()
