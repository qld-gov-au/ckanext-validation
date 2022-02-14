# encoding: utf-8

import click
import commands


@click.group()
def validation():
    """Generates validation commands"""
    pass


@validation.command()
def init_db():
    ''' Initialize database tables.
    '''
    commands.init_db()


@validation.command()
@click.option('-r', '--resource', help='''
Run data validation on a particular resource (if the format is suitable).
It can be defined multiple times. Not to be used with -d or -s''')
@click.option('-d', '--dataset', help='''
Run data validation on all resources for a particular dataset (if the format
is suitable). You can use the dataset id or name, and it can be defined
multiple times. Not to be used with -r or -s''')
@click.option('-s', '--search', help='''Extra search parameters that will be
used for getting the datasets to run validation on. It must be a
JSON object like the one used by the `package_search` API call. Supported
fields are `q`, `fq` and `fq_list`. Check the documentation for examples.
Note that when using this you will have to specify the resource formats to
target yourself. Not to be used with -r or -d.''')
@click.option('-y', '--yes', help='''Automatic yes to prompts. Assume "yes"
as answer to all prompts and run non-interactively''')
def run(resource, dataset):
    '''Start asynchronous data validation on the site resources. If no
    options are provided it will run validation on all resources of
    the supported formats (`ckanext.validation.formats`). You can
    specify particular datasets to run the validation on their
    resources. You can also pass arbitrary search parameters to filter
    the selected datasets.
    '''
    commands.run_validation()


@validation.command()
@click.option('-o', '--output', help='''Location of the CSV validation
report file on the relevant commands.''')
def report(output):
    '''Generate a report with all current data validation reports. This
    will print an overview of the total number of tabular resources
    and a breakdown of how many have a validation status of success,
    failure or error. Additionally it will create a CSV report with all
    failing resources, including the following fields:
        * Dataset name
        * Resource id
        * Resource URL
        * Status
        * Validation report URL
    '''
    commands.report(output)


@validation.command()
@click.option('-o', '--output', help='''Location of the CSV validation
report file on the relevant commands.''')
def report_full(output):
    '''Generate a detailed report. This is similar to 'report'
    but on the CSV report it will add a row for each error found on the
    validation report (limited to ten occurrences of the same error
    type per file). So the fields in the generated CSV report will be:

        * Dataset name
        * Resource id
        * Resource URL
        * Status
        * Error code
        * Error message
    '''
    commands.report(output, full=True)


def get_commands():
    return [validation]
