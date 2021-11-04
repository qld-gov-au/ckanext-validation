import sys
import click
import pprint

from ckanext.validation.model import create_tables, tables_exist


@click.group()
def validation():
    """Validation management commands.
    """
    pass


@validation.command(name='init-db')
def init_db():
    if tables_exist():
        click.echo(pprint.pformat(u'Validation tables already exist'))
        sys.exit(0)

    create_tables()
    click.echo(pprint.pformat(u'Validation tables created'))
