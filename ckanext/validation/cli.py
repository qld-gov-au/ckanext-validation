import click

import ckanext.validation.common as common

def get_commands():
    return [validation]


@click.group()
def validation():
    """Validation management commands.
    """
    pass


@validation.command(name='init-db')
def init_db():
    common.init_db()


@validation.command(name='run')
@click.option(u'-y', u'--yes',
              help=u'Automatic yes to prompts. Assume "yes" as answer '
                   u'to all prompts and run non-interactively',
              default=False)
@click.option('-r', '--resource',
              multiple=True,
              help=u'Run data validation on a particular resource (if the format is suitable).'
                   u'It can be defined multiple times. Not to be used with -d or -s')
@click.option('-d', '--dataset',
              multiple=True,
              help=u'Run data validation on all resources for a particular dataset (if the format is suitable).'
                   u' You can use the dataset id or name, and it can be defined multiple times. '
                   u'Not to be used with -r or -s')
@click.option('-s', '--search',
              default=False,
              help=u'Run data validation on all resources for a particular dataset (if the format is suitable).'
                   u' You can use the dataset id or name, and it can be defined multiple times. '
                   u'Not to be used with -r or -s')
def run_validation(yes, resource, dataset, search):
    common.run_validation(yes, resource, dataset, search)


@validation.command()
@click.option(u'-o', u'--output',
              help=u'Location of the CSV validation report file on the relevant commands.',
              default=u'validation_errors_report.csv')
def report(output):
    common.report(output)


@validation.command(name='report-full')
@click.option(u'-o', u'--output',
              help=u'Location of the CSV validation report file on the relevant commands.',
              default=u'validation_errors_report.csv')
def report_full(output):
    common.report(output)
