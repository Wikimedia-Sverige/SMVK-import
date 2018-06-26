#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Merge two data file pairs (main+archive) from different SMVK-museums.

Since the same file can be found in multiple museums this merges the data files
(and archive card data) for two of these. Outputting a single data + archive
card pair of files using the same format.

Duplicate data is removed and differing data is simply appended.

usage:
    python smvk/mergeFiles.py data1.csv archive1.csv \
    data2.csv archive2.csv [OPTIONS]

&params;
"""
import pywikibot

import batchupload.common as common

from smvk.csvParser import CsvParser

DELIMITER = '¤'
LIST_DELIMITER = '|'
LABEL_DELIMITER = '!'

DEFAULT_OPTIONS = {
    'delimiter': DELIMITER,
    'list_delimiter': LIST_DELIMITER,
    'label_delimiter': LABEL_DELIMITER,
    'orig_data_file': None,
    'orig_archive_file': None,
    'dupe_data_file': None,
    'dupe_archive_file': None,
    'base_name': None
}
PARAMETER_HELP = u"""\
Basic smvk_mergeFiles options:
The first four of these can also be provided as unlabeled arguments.
-orig_data_file:PATH         path to main metadata file
-orig_archive_file:PATH      path to main archive data file
-dupe_data_file:PATH         path to secondary metadata file
-dupe_archive_file:PATH      path to secondary archive data file
-delimiter:STR               string used as delimiter in csv (DEF: {delimiter})
-list_delimiter:STR          string used as list delimiter in csv \
(DEF: {list_delimiter})
-label_delimiter:STR         string used as label delimiter in preserved ids \
(DEF: {label_delimiter})
-base_name:STR               base name to use for output files \
(without file extension)

Can also handle any pywikibot options. Most importantly:
-simulate               don't write to database
-help                   output all available options
"""
docuReplacements = {'&params;': PARAMETER_HELP.format(**DEFAULT_OPTIONS)}


def main(*args):
    """Load arguments and run the merger."""
    options = load_settings(args)
    pywikibot.output('Merger started')
    parser = CsvParser(**options)
    data_files = load_files(parser, options)
    merge_data(data_files, options)
    output_files(parser, data_files, options)
    pywikibot.output('Merger complete')


def load_files(parser, options):
    """Load all four data files."""
    return {
        'main_data': parser.load_data(options.get('orig_data_file')),
        'archive_data': parser.load_archive_data(
            options.get('orig_archive_file'), raw=True),
        'dupe_data': parser.load_data(options.get('dupe_data_file')),
        'dupe_archive_data': parser.load_archive_data(
            options.get('dupe_archive_file'), raw=True)
    }


def merge_data(data_files, options):
    """Merge data from dupe datasets into main datasets."""
    main_data = data_files.get('main_data')
    archive_data = data_files.get('archive_data')
    candidates = populate_candidates(main_data)
    duplicates = {}

    # process dupe_data
    for key, dupe_entry in data_files.get('dupe_data').items():
        orig_photo_id = identify_dupe_id(dupe_entry, candidates, duplicates)
        if orig_photo_id:
            merge_dupe(main_data.get(orig_photo_id), dupe_entry, options)
        else:
            if key in main_data:
                pywikibot.error(
                    '{}: The same photo_id was found in both files.'
                    'Sanitize your data!'.format(key))
            main_data[key] = dupe_entry

    # process dupe_archive_data
    for key, dupe_entry in data_files.get('dupe_archive_data').items():
        archive_data[key] = process_dupe_archive_entry(dupe_entry, duplicates)


def populate_candidates(data):
    """Process orig_data and add any ext_id matches as candidates."""
    candidates = {}
    for entry in data.values():
        if not entry.get('ext_ids'):
            continue
        base_info = {
            'orig_photo_id': entry.get('photo_id'),
            'orig_long_id': '{}/{}'.format(
                entry.get('museum_obj'), entry.get('db_id')),  # needed?
            'dupe_photo_id': None,  # needed?
            'dupe_long_id': None  # needed?
        }

        for ext_id in entry.get('ext_ids'):
            candidates[ext_id] = base_info.copy()
            candidates[ext_id]['dupe_long_id'] = ext_id
    return candidates


def identify_dupe_id(entry, candidates, duplicates):
    """Determine if a dupe_data entry is a dupe and update known dupes."""
    long_id = '{}/{}'.format(entry.get('museum_obj'), entry.get('db_id'))
    if long_id in candidates:
        # move from candidates to known duplicates
        candidate = candidates.pop(long_id)
        candidate['dupe_photo_id'] = entry.get('photo_id')
        duplicates[entry.get('photo_id')] = candidate

        return candidate.get('orig_photo_id')


def merge_dupe(orig_entry, dupe_entry, options):
    """
    Merge dupe_data into orig data.

    Date is handled differently but for all others the value in dupe is simply
    appended to that of original if different.

    Validating the result (e.g. if two licenses were merged) is handled once
    the resulting output gets loaded.
    """
    # remove orig_long_id from ext_ids
    try:
        orig_long_id = '{}/{}'.format(
            orig_entry.get('museum_obj'), orig_entry.get('db_id'))
        dupe_entry.get('ext_ids').remove(orig_long_id)
    except ValueError:
        pass

    # merge each field
    for field, dupe_value in dupe_entry.items():
        orig_value = orig_entry.get(field)
        # handle non-conflicting
        if not dupe_value or (orig_value == dupe_value):
            continue
        elif not orig_value:
            orig_entry[field] = dupe_value
            continue

        # handle conflicting
        if field in ('photo_id', 'db_id', 'museum_obj'):
            # all of these are contained within the ext_ids
            continue
        elif field == 'date':
            # the order and number of the entries has meaning
            pywikibot.warning(
                '{}: Original and dupe dates differ {} != {}. '
                'Discarding the latter.'.format(
                    dupe_entry.get('photo_id'),
                    '-'.join(orig_value),
                    '-'.join(dupe_value)))
        elif field == 'license':
            # if cc0 and PD, choose PD (one contains more info)
            if set([dupe_value, orig_value]) == set(['PD', 'cc0']):
                orig_entry[field] = 'PD'
            else:
                # weirdo license, will get flagged later
                orig_entry[field] += '/{}'.format(dupe_value)
        elif isinstance(dupe_value, list):
            # merge and remove duplicates
            orig_entry[field] = list(
                set(orig_entry.get(field) + dupe_entry.get(field)))
        else:
            if orig_entry.get(field).strip() != dupe_entry.get(field).strip():
                # strings are concatenated
                orig_entry[field] = '{}. {}'.format(
                    orig_entry.get(field).rstrip(' .'),
                    dupe_entry.get(field)).lstrip(' .')

    # add dupe photo_id to the matching ext_id - photo_id
    try:
        dupe_long_id = '{}/{}'.format(
            dupe_entry.get('museum_obj'), dupe_entry.get('db_id'))
        orig_entry.get('ext_ids').remove(dupe_long_id)
        orig_entry.get('ext_ids').append(
            '{}{}{}'.format(dupe_long_id,
                            options.get('label_delimiter'),
                            dupe_entry.get('photo_id')))
    except ValueError:
        pass


def process_dupe_archive_entry(data, duplicates):
    """Take a dupe_archive_data entry and update photo_id if needed."""
    clean_photo_ids = []
    for photo_id in data.get('photo_ids'):
        if photo_id in duplicates:
            orig_photo_id = duplicates.get(photo_id).get('orig_photo_id')
            clean_photo_ids.append(orig_photo_id)
        else:
            clean_photo_ids.append(photo_id)
    data['photo_ids'] = clean_photo_ids
    return data


def output_files(parser, data_files, options):
    """Output the updated datasets as csvs."""
    main_data_file = '{}_merged.csv'.format(options.get('base_name'))
    archive_data_file = '{}_merged_arkiv.csv'.format(options.get('base_name'))

    parser.output_data(data_files.get('main_data'), main_data_file)
    parser.output_archive_data(
        data_files.get('archive_data'), archive_data_file)


def handle_args(args, usage):
    """
    Parse and load all of the basic arguments.

    Also passes any needed arguments on to pywikibot and sets any defaults.

    :param args: arguments to be handled
    :return: dict of options
    """
    options = {}
    arg_counter = 0
    arg_map = ['orig_data_file', 'orig_archive_file',
               'dupe_data_file', 'dupe_archive_file']

    for arg in pywikibot.handle_args(args):
        option, sep, value = arg.partition(':')
        if not sep:  # unlabeled argument.
            options[arg_map[arg_counter]] = option
            arg_counter += 1
        elif option.startswith('-') and option[1:] in DEFAULT_OPTIONS.keys():
            options[option[1:]] = common.convert_from_commandline(value)
        else:
            pywikibot.output(usage)
            exit()

    if arg_counter not in (0, 4):
        pywikibot.error(
            'Either all filenames are passed as unlabeled arguments or none.')

    return options


def load_settings(args):
    """
    Load settings from command line or defaults.

    Any command line values takes precedence over defaults values.
    """
    default_options = DEFAULT_OPTIONS.copy()
    usage = PARAMETER_HELP.format(**default_options)
    options = handle_args(args, usage)

    # combine all loaded settings
    for key, val in default_options.items():
        options[key] = options.get(key) or val

    if any(val is None for val in options.values()):
        pywikibot.error('All required arguments must be provided.')
        pywikibot.output(usage)
        exit()

    return options


if __name__ == '__main__':
    main()
