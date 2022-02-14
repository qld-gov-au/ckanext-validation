# encoding: utf-8

import sys
import logging
import csv

from ckan.lib.cli import query_yes_no
from ckantoolkit import get_action, config

from ckanext.validation import settings
from ckanext.validation.model import create_tables, tables_exist
from ckanext.validation.logic import _search_datasets

log = logging.getLogger(__name__)

_page_size = 100


def error(msg):
    '''
    Print an error message to STDOUT and exit with return code 1.
    '''
    sys.stderr.write(msg)
    if not msg.endswith('\n'):
        sys.stderr.write('\n')
    sys.exit(1)


def init_db():

    if tables_exist():
        print(u'Validation tables already exist')
        sys.exit(0)

    create_tables()

    print(u'Validation tables created')


def run_validation(resource_ids, dataset_ids, search_params=None, assume_yes=False):
    if resource_ids:
        for resource_id in resource_ids:
            resource = get_action('resource_show')({}, {'id': resource_id})
            _run_validation_on_resource(
                resource['id'], resource['package_id'])
    else:
        query = _search_datasets()

        if query['count'] == 0:
            error('No suitable datasets, exiting...')

        elif not assume_yes:
            msg = ('\nYou are about to start validation for {0} datasets'
                   + '.\n Do you want to continue?')

            if query_yes_no(msg.format(query['count'])) == 'no':
                error('Command aborted by user')

        result = get_action('resource_validation_run_batch')(
            {'ignore_auth': True},
            {'dataset_ids': dataset_ids,
             'query': search_params}
        )
        print(result['output'])


def _run_validation_on_resource(resource_id, dataset_id):
    get_action(u'resource_validation_run')(
        {u'ignore_auth': True},
        {u'resource_id': resource_id,
         u'async': True})

    log.debug('Resource %s from dataset %s sent to the validation queue',
              resource_id, dataset_id)


def _process_row(dataset, resource, writer):
    resource_url = '{}/dataset/{}/resource/{}'.format(
        config['ckan.site_url'],
        dataset['name'],
        resource['id'])

    validation_url = resource_url + '/validation'

    writer.writerow({
        'dataset': dataset['name'],
        'resource_id': resource['id'],
        'format': resource['format'],
        'url': resource_url,
        'status': resource['validation_status'],
        'validation_report_url': validation_url
    })

    return


def _process_row_full(dataset, resource, writer):
    limit_per_error_type = 10

    error_counts = {}

    resource_url = '{}/dataset/{}/resource/{}'.format(
        config['ckan.site_url'],
        dataset['name'],
        resource['id'])

    # Get validation report
    validation = get_action('resource_validation_show')(
        {'ignore_auth': True}, {'resource_id': resource['id']})

    if not validation.get('report'):
        return

    errors = validation['report']['tables'][0]['errors']

    for error in errors:
        if not error['code'] in error_counts:
            error_counts[error['code']] = 1
        else:
            error_counts[error['code']] += 1

        if error_counts[error['code']] > limit_per_error_type:
            continue

        writer.writerow({
            'dataset': dataset['name'],
            'resource_id': resource['id'],
            'format': resource['format'],
            'url': resource_url,
            'status': resource['validation_status'],
            'error_code': error['code'],
            'error_message': error['message']
        })

    return error_counts


def report(output_file, full=False):
    if output_file == 'validation_errors_report.csv' and full:
        output_file = 'validation_errors_report_full.csv'

    outputs = {
        'tabular_resources': 0,
        'resources_failure': 0,
        'resources_error': 0,
        'resources_success': 0,
        'datasets': 0,
        'formats_success': {},
        'formats_failure': {}
    }
    error_counts = {}

    with open(output_file, 'w') as fw:
        if full:
            fieldnames = [
                'dataset', 'resource_id', 'format', 'url',
                'status', 'error_code', 'error_message']
        else:
            fieldnames = [
                'dataset', 'resource_id', 'format', 'url',
                'status', 'validation_report_url']

        writer = csv.DictWriter(fw, fieldnames=fieldnames)
        writer.writeheader()

        page = 1
        while True:
            query = _search_datasets(page)

            if page == 1 and query['count'] == 0:
                error('No suitable datasets, exiting...')

            if query['results']:
                for dataset in query['results']:

                    if not dataset.get('resources'):
                        continue

                    for resource in dataset['resources']:

                        if (not resource['format'].lower() in
                                settings.DEFAULT_SUPPORTED_FORMATS):
                            continue

                        outputs['tabular_resources'] += 1

                        if resource.get('validation_status'):
                            outputs['resources_' + resource['validation_status']] += 1

                        if resource.get('validation_status') in (
                                'failure', 'error'):
                            if full:
                                row_counts = _process_row_full(dataset, resource, writer)
                                if not row_counts:
                                    continue
                                for code, count in row_counts.iteritems():
                                    if code not in error_counts:
                                        error_counts[code] = count
                                    else:
                                        error_counts[code] += count
                            else:
                                _process_row(dataset, resource, writer)

                            if resource['format'] in outputs['formats_failure']:
                                outputs['formats_failure'][resource['format']] += 1
                            else:
                                outputs['formats_failure'][resource['format']] = 1
                        else:
                            if resource['format'] in outputs['formats_success']:
                                outputs['formats_success'][resource['format']] += 1
                            else:
                                outputs['formats_success'][resource['format']] = 1

                if len(query['results']) < _page_size:
                    break

                page += 1
            else:
                break

    outputs['datasets'] = query['count']
    outputs['output_csv'] = output_file

    outputs['formats_success_output'] = ''
    for count, code in sorted([(v, k) for k, v in outputs['formats_success'].iteritems()], reverse=True):
        outputs['formats_success_output'] += '* {}: {}\n'.format(code, count)

    outputs['formats_failure_output'] = ''
    for count, code in sorted([(v, k) for k, v in outputs['formats_failure'].iteritems()], reverse=True):
        outputs['formats_failure_output'] += '* {}: {}\n'.format(code, count)

    error_counts_output = ''
    if full:
        for count, code in sorted([(v, k) for k, v in error_counts.iteritems()], reverse=True):
            error_counts_output += '* {}: {}\n'.format(code, count)

    outputs['error_counts_output'] = error_counts_output

    msg_errors = '''
Errors breakdown:
{}
'''.format(outputs['error_counts_output'])

    outputs['msg_errors'] = msg_errors if full else ''

    msg = '''
Done.
{datasets} datasets with tabular resources
{tabular_resources} tabular resources
{resources_success} resources - validation success
{resources_failure} resources - validation failure
{resources_error} resources - validation error

Formats breakdown (validation passed):
{formats_success_output}
Formats breakdown (validation failed or errored):
{formats_failure_output}
{msg_errors}
CSV Report stored in {output_csv}
'''.format(**outputs)

    log.info(msg)
