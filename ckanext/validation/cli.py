import click


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
