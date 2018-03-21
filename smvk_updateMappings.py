#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Create or update mapping lists.

usage:
    python smvk_updateMappings.py [OPTIONS]

&params;
"""
import os.path as path
from collections import Counter, OrderedDict

import pywikibot

import batchupload.common as common
import batchupload.csv_methods as csv_methods
import batchupload.helpers as helpers
from batchupload.listscraper import MappingList

import smvk_utils as utils

MAPPINGS_DIR = 'mappings'
DATA_FILE = 'smvk_data.csv'
ARCHIVE_FILE = 'smvk_data_arkiv.csv'
LOGFILE = 'smvk_mappings.log'
DELIMITER = '¤'
LIST_DELIMITER = '|'

DEFAULT_OPTIONS = {
    'data_file': DATA_FILE,
    'archive_file': ARCHIVE_FILE,
    'mapping_log_file': LOGFILE,
    'mappings_dir': MAPPINGS_DIR,
    'delimiter': DELIMITER,
    'list_delimiter': LIST_DELIMITER,
    'wiki_mapping_root': 'Commons:Världskulturmuseerna/mapping',
    'default_intro_text': ('{key} mapping table for '
                           '[[Commons:Världskulturmuseerna]]\n')
}
PARAMETER_HELP = u"""\
Basic smvk_updateMappings options:
-data_file:PATH         path to main metadata file (DEF: {data_file})
-archive_file:PATH      path to archive data file (DEF: {archive_file})
-mapping_log_file:PATH  path to mappings log file (DEF: {mapping_log_file})
-mappings_dir:PATH      path to mappings dir (DEF: {mappings_dir})
-delimiter:STR          string used as delimiter in csv (DEF: {delimiter})
-list_delimiter:STR     string used as list delimiter in csv \
(DEF: {list_delimiter})
-wiki_mapping_root:PATH path to wiki mapping root (DEF: {wiki_mapping_root})
-default_intro_text:STR default text to add to the top of each mapping table \
page. Should contain the {{key}} format variable (DEF: {default_intro_text})

Can also handle any pywikibot options. Most importantly:
-simulate               don't write to database
-help                   output all available options
"""
docuReplacements = {'&params;': PARAMETER_HELP.format(**DEFAULT_OPTIONS)}


class SMVKMappingUpdater(object):
    """Update mappings based on provided SMVK data."""

    def __init__(self, options):
        """Initialise an mapping updater for a SMVK dataset."""
        self.settings = options

        self.log = common.LogFile('', self.settings.get('mapping_log_file'))
        self.log.write_w_timestamp('Updater started...')
        self.mappings = load_mappings(
            update_mappings=True,
            mappings_dir=self.settings.get('mappings_dir'))
        data = load_data(self.settings.get('data_file'),
                         delimiter=self.settings.get('delimiter'),
                         list_delimiter=self.settings.get('list_delimiter'))
        # load archive card data to ensure formatting is still valid
        archive_data = load_archive_data(
            self.settings.get('archive_file'),
            delimiter=self.settings.get('delimiter'),
            list_delimiter=self.settings.get('list_delimiter'))

        self.people_to_map = Counter()
        self.ethnic_to_map = Counter()
        self.places_to_map = OrderedDict()
        self.keywords_to_map = Counter()
        self.expedition_to_match = set()
        self.museum_to_match = set()
        self.external_to_parse = set()

        self.parse_data(data)
        self.parse_archive_data(archive_data)

        # validate hard coded mappings
        for ext_id in self.external_to_parse:
            utils.parse_external_ids(ext_id)
        for expedition in self.expedition_to_match:
            if expedition not in self.mappings.get('expeditions'):
                pywikibot.warning(
                    '{} must be added to expeditions.json'.format(expedition))
        museum_mapping = self.mappings.get('museums')
        for museum, type in self.museum_to_match:
            if museum not in museum_mapping:
                pywikibot.warning(
                    '{} must be added to museum.json'.format(museum))
            elif type not in museum_mapping.get(museum).get('known_types'):
                pywikibot.warning(
                    'The "{}" type for {} must be added the Wikimedia link '
                    'templates and to museum.json'.format(type, museum))

        self.dump_to_wikifiles()

    def dump_to_wikifiles(self):
        """Dump the mappings to wikitext files."""
        self.dump_places()
        self.dump_keywords()
        self.dump_people()
        self.dump_ethnic()

    def get_intro_text(self, key):
        """Return the specific info text for a list or the default one."""
        return self.settings.get('default_intro_text').format(
            key=key.title())

    def dump_places(self):
        """
        Dump the place mappings to wikitext files.

        Although dumped to one page each type is dumped as a separate table
        """
        ml = make_places_list(
            mapping_root=self.settings.get('wiki_mapping_root'))
        intro_text = self.get_intro_text('places')
        merged_places, preserved_places = ml.multi_table_mappings_merger(
            self.places_to_map, update=True)
        ml.save_as_wikitext(merged_places, preserved_places, intro_text)

    def dump_keywords(self):
        """Dump the keyword mappings to wikitext files."""
        mk = make_keywords_list(
            mapping_root=self.settings.get('wiki_mapping_root'))
        intro_text = self.get_intro_text('keyword')
        merged_keywords, preserved_keywords = mk.mappings_merger(
            self.keywords_to_map.most_common(), update=True)
        mk.save_as_wikitext(merged_keywords, preserved_keywords, intro_text)

    def dump_ethnic(self):
        """Dump the ethnic group mappings to wikitext files."""
        me = make_ethnic_list(
            mapping_root=self.settings.get('wiki_mapping_root'))
        intro_text = self.get_intro_text('ethnic groups')
        merged_ethnic, preserved_ethnic = me.mappings_merger(
            self.ethnic_to_map.most_common(), update=True)
        me.save_as_wikitext(merged_ethnic, preserved_ethnic, intro_text)

    def dump_people(self):
        """Dump the people mappings to wikitext files."""
        mp = make_people_list(
            mapping_root=self.settings.get('wiki_mapping_root'))
        intro_text = self.get_intro_text('people')
        merged_people, preserved_people = mp.mappings_merger(
            self.people_to_map.most_common(), update=True)
        mp.save_as_wikitext(merged_people, preserved_people, intro_text)

    def check_for_unexpected_lists(self, data, label):
        """
        Ensure there aren't any unexpected lists.

        :param data: a single image or archive card entry
        :param label: label allowing the row to be identified in the csv
        """
        delimiter = self.settings.get('list_delimiter')
        if any(delimiter in entry for entry in data.values()):
            raise common.MyError(
                '{}: One of the columns unexpectedly '
                'contains a list\n{}'.format(
                    label,
                    '\n'.join(
                        ['{}: {}'.format(k, v) for k, v in filter(
                            lambda x: delimiter in x[1], data.items())]
                    )))

    def parse_archive_data(self, data):
        """Go through the raw data breaking out data needing validating."""
        for cards in data.values():
            for card in cards:
                self.check_for_unexpected_lists(card, card.get('photo_id'))

                if card.get('museum_obj'):
                    museum, _, type = card.get('museum_obj').partition('/')
                    self.museum_to_match.add((museum, type))

    def parse_data(self, data):
        """Go through the raw data breaking out data needing mapping."""
        for key, image in data.items():
            self.check_for_unexpected_lists(image, image.get('photo_id'))

            if image.get('event'):
                self.expedition_to_match.update(
                    utils.clean_uncertain(
                        common.listify(image.get('event')),
                        keep=True))
            if image.get('museum_obj'):
                museum, _, type = image.get('museum_obj').partition('/')
                self.museum_to_match.add((museum, type))
            if image.get('ext_id'):
                self.external_to_parse.update(
                    image.get('ext_id'))

            # keywords - compare without case
            keyword_columns = ('motivord', 'sokord')
            for col in keyword_columns:
                val = image.get(col) or []
                val = utils.clean_uncertain(common.listify(val), keep=True)
                val = [v.casefold() for v in val]
                self.keywords_to_map.update(val)

            # people
            people_columns = ('depicted_persons', 'photographer', 'creator')
            for col in people_columns:
                val = image.get(col) or []
                val = utils.clean_uncertain(common.listify(val), keep=True)
                self.people_to_map.update([helpers.flip_name(person)
                                           for person in val])

            # ethnic groups - compare without case
            ethnic_columns = ('ethnic', 'ethnic_old')
            for col in ethnic_columns:
                val = image.get(col) or []
                val = utils.clean_uncertain(common.listify(val), keep=True)
                val = [v.casefold() for v in val]
                self.ethnic_to_map.update(val)

            # places
            place_columns = ('land', 'region', 'ort', 'depicted_places')
            for col in place_columns:
                if col not in self.places_to_map:
                    self.places_to_map[col] = Counter()
                val = image.get(col) or []
                val = utils.clean_uncertain(common.listify(val), keep=True)
                self.places_to_map[col].update(val)


def load_data(csv_file, delimiter=None, list_delimiter=None):
    """
    Load and parse the provided csv file.

    This only parses the main metadata file, not that for archive_cards.
    This is the only place where the original column names should be mentioned.

    :param csv_file: the filename to load
    :param delimiter: the delimiter to use for csv cells
    :param list_delimiter: the delimiter to use for lists within csv cells
    """
    delimiter = delimiter or DELIMITER
    list_delimiter = list_delimiter or LIST_DELIMITER
    fields = OrderedDict([
        ('Fotonummer', 'photo_id'),
        ('Beskrivning', 'description_sv'),
        ('Motivord', 'motivord'),
        ('Sökord', 'sokord'),
        ('Händelse', 'event'),
        ('Etnisk grupp', 'ethnic'),
        ('Personnamn, avbildad', 'depicted_persons'),
        ('Land, Fotograferad', 'land'),
        ('Region, fotograferad i', 'region'),
        ('Ort, fotograferad i', 'ort'),
        ('Geografiskt namn, annat', 'other_geo'),
        ('Fotograf', 'photographer'),
        ('Fotodatum', 'date'),
        ('Personnamn / tillverkare', 'creator'),
        ('Beskrivning, engelska', 'description_en'),
        ('Referens / Publicerad i', 'reference_published'),
        ('Postnr.', 'db_id'),
        ('Objekt, externt / samma som', 'ext_id'),
        ('Etn, tidigare', 'ethnic_old'),
        ('Land, ursprung/brukad', 'depicted_land'),
        ('Region/Ort, ursprung', 'depicted_places'),
        ('Referens / källa', 'reference_source'),
        ('Media/Licens', 'license'),
        ('Museum/objekt', 'museum_obj')
    ])

    expected_header = delimiter.join(fields.keys())
    list_columns = (
        'Motivord', 'Sökord', 'Etnisk grupp', 'Personnamn, avbildad',
        'Region, fotograferad i', 'Ort, fotograferad i',
        'Geografiskt namn, annat', 'Fotodatum', 'Objekt, externt / samma som',
        'Region/Ort, ursprung', 'Referens / Publicerad i')
    raw_dict = csv_methods.csv_file_to_dict(
        csv_file, 'Fotonummer', expected_header, lists=list_columns,
        delimiter=delimiter,
        list_delimiter=list_delimiter)

    return utils.relabel_inner_dicts(raw_dict, fields)


def load_archive_data(csv_file, delimiter=None, list_delimiter=None):
    """
    Load and parse the provided csv file for archive_cards.

    This only parses the archive_cards file, not that for the main metadata.
    This is the only place where the original column names should be mentioned.

    :param csv_file: the filename to load
    :param delimiter: the delimiter to use for csv cells
    :param list_delimiter: the delimiter to use for lists within csv cells
    """
    delimiter = delimiter or DELIMITER
    list_delimiter = list_delimiter or LIST_DELIMITER
    fields = OrderedDict([
        ('Id', 'label'),
        ('Postnr', 'db_id'),
        ('Museum/objekt', 'museum_obj'),
        ('Fotonummer', 'photo_id')])

    expected_header = delimiter.join(fields.keys())
    list_columns = ('Fotonummer', )
    raw_dict = csv_methods.csv_file_to_dict(
        csv_file, 'Postnr', expected_header, lists=list_columns,
        delimiter=delimiter,
        list_delimiter=list_delimiter)
    relabeled_dict = utils.relabel_inner_dicts(raw_dict, fields)

    # re-order so photo_id is main key
    photo_id_dict = {}
    for k, v in relabeled_dict.items():
        for photo_id in v.get('photo_id'):
            if photo_id not in photo_id_dict:
                photo_id_dict[photo_id] = []
            photo_id_dict[photo_id].append(v)
    return photo_id_dict


def load_mappings(update_mappings, mappings_dir=None,
                  load_mapping_lists=None):
    """
    Update mapping files, load these and package appropriately.

    :param update_mappings: whether to first download the latest mappings
    :param mappings_dir: path to directory in which mappings are found
    :param load_mapping_lists: the root path to any mapping_lists which should
        be loaded.
    """
    mappings = {}
    mappings_dir = mappings_dir or MAPPINGS_DIR
    common.create_dir(mappings_dir)  # ensure it exists

    expeditions_file = path.join(mappings_dir, 'expeditions.json')
    museums_file = path.join(mappings_dir, 'museums.json')

    # static files
    mappings['expeditions'] = common.open_and_read_file(
        expeditions_file, as_json=True)
    mappings['museums'] = common.open_and_read_file(
        museums_file, as_json=True)

    if load_mapping_lists:
        load_mapping_lists_mappings(
            mappings_dir, update_mappings, mappings, load_mapping_lists)

    pywikibot.output('Loaded all mappings')
    return mappings


def load_mapping_lists_mappings(
        mappings_dir, update=True, mappings=None, mapping_root=None):
    """
    Add mapping lists to the loaded mappings.

    :param update: whether to first download the latest mappings
    :param mappings_dir: path to directory in which mappings are found
    :param mappings: dict to which mappings should be added. If None then a new
        dict is returned.
    :param mapping_root: root path for the mappings on wiki (required for an
        update)
    """
    mappings = mappings or {}
    mappings_dir = mappings_dir or MAPPINGS_DIR
    if update and not mapping_root:
        raise common.MyError('A mapping root is needed to load new updates.')

    ml = make_places_list(mappings_dir, mapping_root)
    mappings['places'] = ml.consume_entries(
        ml.load_old_mappings(update=update), 'name',
        require=['category', 'wikidata'])

    mk = make_keywords_list(mappings_dir, mapping_root)
    mappings['keywords'] = mk.consume_entries(
        mk.load_old_mappings(update=update), 'name', require='category',
        only='category')

    mp = make_people_list(mappings_dir, mapping_root)
    mappings['people'] = mp.consume_entries(
        mp.load_old_mappings(update=update), 'name',
        require=['creator', 'category', 'wikidata'])

    me = make_ethnic_list(mappings_dir, mapping_root)
    mappings['ethnic'] = me.consume_entries(
        me.load_old_mappings(update=update), 'name',
        require=['category', 'wikidata'])
    return mappings


def make_places_list(mapping_dir=None, mapping_root=None):
    """Create a MappingList object for places."""
    mapping_dir = mapping_dir or MAPPINGS_DIR
    mapping_root = mapping_root or 'dummy'
    parameters = ['name', 'category', 'wikidata', 'frequency']
    header = '{{User:André Costa (WMSE)/mapping-head|category=|wikidata=}}'
    return MappingList(
        page='{}/places'.format(mapping_root),
        parameters=parameters,
        header_template=header,
        mapping_dir=mapping_dir)


def make_keywords_list(mapping_dir=None, mapping_root=None):
    """Create a MappingList object for keywords."""
    mapping_dir = mapping_dir or MAPPINGS_DIR
    mapping_root = mapping_root or 'dummy'
    parameters = ['name', 'category', 'frequency']
    header = '{{User:André Costa (WMSE)/mapping-head|category=}}'
    return MappingList(
        page='{}/keywords'.format(mapping_root),
        parameters=parameters,
        header_template=header,
        mapping_dir=mapping_dir)


def make_people_list(mapping_dir=None, mapping_root=None):
    """Create a MappingList object for people."""
    mapping_dir = mapping_dir or MAPPINGS_DIR
    mapping_root = mapping_root or 'dummy'
    parameters = ['name', 'more', 'creator', 'category', 'wikidata',
                  'frequency']
    header = ('{{User:André Costa (WMSE)/mapping-head'
              '|category=|creator=|wikidata=}}')
    return MappingList(
        page='{}/people'.format(mapping_root),
        parameters=parameters,
        header_template=header,
        mapping_dir=mapping_dir)


def make_ethnic_list(mapping_dir=None, mapping_root=None):
    """Create a MappingList object for ethinc groups."""
    mapping_dir = mapping_dir or MAPPINGS_DIR
    mapping_root = mapping_root or 'dummy'
    parameters = ['name', 'more', 'category', 'wikidata',
                  'frequency']
    header = ('{{User:André Costa (WMSE)/mapping-head'
              '|category=|wikidata=}}')
    return MappingList(
        page='{}/ethnic_groups'.format(mapping_root),
        parameters=parameters,
        header_template=header,
        mapping_dir=mapping_dir)


def handle_args(args, usage):
    """
    Parse and load all of the basic arguments.

    Also passes any needed arguments on to pywikibot and sets any defaults.

    :param args: arguments to be handled
    :return: dict of options
    """
    options = {}
    expected_args = ('mapping_log_file', 'data_file', 'archive_file',
                     'mappings_dir', 'delimiter', 'list_delimiter',
                     'wiki_mapping_root', 'default_intro_text')

    for arg in pywikibot.handle_args(args):
        option, sep, value = arg.partition(':')
        if option.startswith('-') and option[1:] in expected_args:
            options[option[1:]] = common.convert_from_commandline(value)
        else:
            pywikibot.output(usage)
            exit()

    return options


def load_settings(args):
    """
    Load settings from command line or defaults.

    Any command line values takes precedence over defaults values.
    """
    default_options = DEFAULT_OPTIONS.copy()

    options = handle_args(args, PARAMETER_HELP.format(**default_options))

    # combine all loaded settings
    for key, val in default_options.items():
        options[key] = options.get(key) or val

    return options


def main(*args):
    """Initialise and run the mapping updater."""
    options = load_settings(args)
    updater = SMVKMappingUpdater(options)
    updater.log.write_w_timestamp('...Updater finished\n')
    pywikibot.output(updater.log.close_and_confirm())


if __name__ == '__main__':
    main()
