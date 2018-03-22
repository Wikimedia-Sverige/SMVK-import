#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Construct image information templates and categories for SMVK data.

These templates are always Photograph independent on the image type.

Transforms the csv data into a BatchUploadTools compliant json file.
"""
from collections import OrderedDict
from datetime import datetime
import os.path as path

import pywikibot

import batchupload.common as common
import batchupload.helpers as helpers
import batchupload.listscraper as listscraper
from batchupload.make_info import MakeBaseInfo

import smvk_updateMappings as mapping_updater
import smvk_utils as utils

MAPPINGS_DIR = 'mappings'
BATCH_CAT = 'Media contributed by SMVK'  # stem for maintenance categories
BATCH_DATE = '2018-03'  # branch for this particular batch upload
BASE_NAME = u'smvk_data'
LOGFILE = 'smvk_processing.log'
GEO_ORDER = ('ort', 'region', 'depicted_places', 'land', 'depicted_land')
GEO_LABELS = {
    'ort': {'sv': 'ort', 'en': 'community'},
    'region': {'sv': 'region', 'en': 'region'},
    'depicted_places': {'sv': 'ursprungsplats', 'en': 'place of origin'},
    'depicted_land': {'sv': 'ursprungsland', 'en': 'country of origin'},
    'land': {'sv': 'land', 'en': 'country'},
    'other_geo': {'sv': 'annan', 'en': 'other'},
}
DATA_FILE = 'smvk_data.csv'


class SMVKInfo(MakeBaseInfo):
    """Construct descriptions + filenames for a Nordic Museum batch upload."""

    def __init__(self, **options):
        """Initialise a make_info object."""
        batch_date = common.pop(options, 'batch_label') or BATCH_DATE
        batch_cat = common.pop(options, 'base_meta_cat') or BATCH_CAT
        super(SMVKInfo, self).__init__(batch_cat, batch_date, **options)

        self.commons = pywikibot.Site('commons', 'commons')
        self.wikidata = pywikibot.Site('wikidata', 'wikidata')
        self.category_cache = {}  # cache for category_exists()
        self.wikidata_cache = {}  # cache for Wikidata results
        self.log = common.LogFile('', LOGFILE)
        self.log.write_w_timestamp('Make info started...')
        self.pd_year = datetime.now().year - 70

    def load_data(self, in_file):
        """
        Load the provided csv data files.

        Return this as a dict with an entry per file which can be used for
        further processing.

        :param in_file: a tuple of paths to the metadata files
        :return: dict
        """
        main_data = mapping_updater.load_data(in_file[0])
        archive_data = mapping_updater.load_archive_data(in_file[1])
        return {'main': main_data, 'archive': archive_data}

    def load_mappings(self, update_mappings):
        """
        Update mapping files, load these and package appropriately.

        :param update_mappings: whether to first download the latest mappings
        """
        self.mappings = mapping_updater.load_mappings(
            update_mappings,
            load_mapping_lists='Commons:Världskulturmuseerna/mapping')

    def mapped_and_wikidata(self, entry, mapping):
        """
        Add the linked wikidata info to a mapping.

        Where mapping list data and Wikidata data differ, list data takes
        precedence.
        """
        if entry in mapping:
            mapped_info = mapping.get(entry)
            if mapped_info.get('enriched'):
                return mapped_info

            if mapped_info.get('wikidata'):
                wd_data = self.get_wikidata_info(mapped_info.get('wikidata'))
                for k, v in wd_data.items():
                    mapped_info[k] = mapped_info.get(k) or v
                # category has different labels in list data and Wikidata
                # and the former is a list. Merge them
                commonscat = mapped_info.pop('commonscat')
                if commonscat:
                    mapped_info['category'].append(commonscat)
                    mapped_info['category'] = list(
                        set(mapped_info['category']))
            mapped_info['enriched'] = True  # no need to do this again
            return mapped_info
        return {}

    def process_data(self, raw_data):
        """
        Take the loaded data and construct a SMVKItem for each.

        Populates self.data but filters out, and logs, any problematic entries.

        :param raw_data: output from load_data()
        """
        self.data = {}
        for key, main_value in raw_data.get('main').items():
            archive_value = raw_data.get('archive').get(key)
            self.data[key] = SMVKItem(main_value, archive_value, self)

        # remove all problematic entries
        problematic = list(
            filter(lambda x: self.data[x].problems, self.data.keys()))
        for key in problematic:
            item = self.data.pop(key)
            text = '{0} -- image was skipped because of: {1}'.format(
                item.photo_id, '\n'.join(item.problems))
            pywikibot.output(text)
            self.log.write(text)

    def generate_filename(self, item):
        """
        Given an item (dict) generate an appropriate filename.

        The filename has the shape: descr - Collection - id
        and does not include filetype

        :param item: the metadata for the media file in question
        :return: str
        """
        return helpers.format_filename(
            item.get_title_description(), 'SMVK', item.photo_id)

    def make_info_template(self, item):
        """
        Given an item of any type return the filled out template.

        :param item: the metadata for the media file in question
        :return: str
        """
        if item.is_photo():
            return self.make_photograph_template(item)
        else:
            return self.make_artwork_info(item)

    def make_photograph_template(self, item):
        """
        Create the Photograph template for a single SMVK entry.

        :param item: the metadata for the media file in question
        :return: str
        """
        template_name = 'Photograph'
        template_data = OrderedDict()
        template_data['photographer'] = item.get_creator_name()
        template_data['title'] = ''
        template_data['description'] = item.get_description()
        template_data['original description info'] = (
            '{{SMVK description/i18n}}')
        template_data['original description'] = item.get_original_description()
        template_data['depicted people'] = item.get_depicted_person()
        template_data['depicted place'] = item.get_depicted_place()
        template_data['date'] = item.date_text
        template_data['institution'] = (
            '{{Institution:Statens museer för världskultur}}')
        template_data['department'] = item.get_museum_link()
        template_data['references'] = item.get_references()
        template_data['notes'] = item.get_notes()
        template_data['accession number'] = item.get_id_link()
        template_data['source'] = item.get_source()
        template_data['permission'] = item.license_text
        template_data['other_versions'] = ''

        return helpers.output_block_template(template_name, template_data, 0)

    def make_artwork_info(self, item):
        """
        Create the Artwork template for a single SMVK entry.

        :param item: the metadata for the media file in question
        :return: str
        """
        template_name = 'Artwork'
        template_data = OrderedDict()
        template_data['artist'] = item.get_creator_name()
        template_data['title'] = ''
        template_data['date'] = item.date_text
        template_data['other_fields_1'] = item.get_original_description(
            wrap=True)
        template_data['description'] = item.get_description(with_depicted=True)
        template_data['medium'] = ''
        template_data['dimensions'] = ''
        template_data['institution'] = (
            '{{Institution:Statens museer för världskultur}}')
        template_data['department'] = item.get_museum_link()
        template_data['location'] = ''
        template_data['references'] = item.get_references()
        template_data['object history'] = ''
        template_data['credit line'] = ''
        template_data['notes'] = item.get_notes()
        template_data['accession number'] = item.get_id_link()
        template_data['source'] = item.get_source()
        template_data['permission'] = item.license_text
        template_data['other_versions'] = ''

        return helpers.output_block_template(template_name, template_data, 0)

    def generate_content_cats(self, item):
        """
        Extract any mapped keyword categories or depicted categories.

        :param item: the SMVKItem to analyse
        :return: list of categories (without "Category:" prefix)
        """
        item.make_item_keyword_categories()
        item.make_ethnic_categories()

        # Add geo categorisation when needed
        if item.needs_place_cat:
            item.make_place_category()

        return list(item.content_cats)

    def generate_meta_cats(self, item, content_cats):
        """
        Produce maintenance categories related to a media file.

        :param item: the metadata for the media file in question
        :param content_cats: any content categories for the file
        :return: list of categories (without "Category:" prefix)
        """
        cats = set([self.make_maintenance_cat(cat) for cat in item.meta_cats])
        cats.add(self.batch_cat)

        # problem cats
        if not content_cats:
            cats.add(self.make_maintenance_cat('needing categorisation'))

        # creator and event cats are classified as meta
        event_cats = item.make_event_categories()
        if event_cats:
            cats.add(event_cats)
        creator_cats = item.get_creator_data().get('category', [])
        if creator_cats:
            cats.update(creator_cats)

        return list(cats)

    def build_link_template(self, museum_obj, id, label):
        """
        Construct an SMVK link template.

        :param museum_obj: a museum/type string
        :param id: unique db id
        :param label: the text to display
        """
        museum, _, type = museum_obj.partition('/')
        prefix = ''
        if museum != 'SMVK-MM':  # MM has prefix as part of id
            prefix = '|{}'.format(type)
        return '{{SMVK-%s-link%s|%s|%s}}' % (
            self.mappings.get('museums').get(museum).get('code'),
            prefix, id, label)

    def get_original_filename(self, item):
        """Return the original image filename without file extension."""
        return item.photo_id

    def get_wikidata_info(self, qid):
        """
        Wrap listscraper.get_wikidata_info with local variables.

        :param qid: Qid for the Wikidata item
        :return: bool
        """
        return listscraper.get_wikidata_info(
            qid, site=self.wikidata, cache=self.wikidata_cache)

    def category_exists(self, cat):
        """
        Wrap helpers.self.category_exists with local variables.

        :param cat: category name (with or without "Category" prefix)
        :return: bool
        """
        return helpers.category_exists(
            cat, site=self.commons, cache=self.category_cache)

    @staticmethod
    def handle_args(args):
        """Parse and load all of the basic arguments.

        Need to override the basic argument handler since we want two
        input files. Also construct a base_name fallback option from these.

        @param args: arguments to be handled
        @type args: list of strings
        @return: list of options
        @rtype: dict
        """
        options = {
            'in_file': None,
            'base_name': None,
            'update_mappings': True,
            'base_meta_cat': None,
            'batch_label': None
        }
        smvk_options = {
            'metadata_file': None,
            'archive_file': None,
        }

        for arg in pywikibot.handle_args(args):
            option, sep, value = arg.partition(':')
            if option == '-data_file':
                smvk_options['data_file'] = common.convert_from_commandline(
                    value)
            elif option == '-archive_file':
                smvk_options['archive_file'] = common.convert_from_commandline(
                    value)
            elif option == '-base_name':
                options['base_name'] = common.convert_from_commandline(value)
            elif option == '-update_mappings':
                options['update_mappings'] = common.interpret_bool(value)
            elif option == '-base_meta_cat':
                options['base_meta_cat'] = common.convert_from_commandline(
                    value)
            elif option == '-batch_label':
                options['batch_label'] = common.convert_from_commandline(value)

        if smvk_options['data_file'] and smvk_options['archive_file']:
            options['in_file'] = \
                (smvk_options['data_file'], smvk_options['archive_file'])
            options['base_name'] = options.get('base_name') or path.join(
                path.split(smvk_options['data_file'])[0],
                BASE_NAME)
        # main handles the case of missing in_files

        return options

    @classmethod
    def main(cls, *args):
        """Command line entry-point."""
        usage = (
            'Usage:'
            '\tpython smvk_makeInfo.py -metadata_file:PATH -archive_file:PATH '
            '-dir:PATH\n'
            '\t-data_file:PATH path to main metadata file\n'
            '\t-archive_file:PATH path to archive card metadata file\n'
            '\t-base_name:STR base name to use for output files\n'
            '\t-dir:PATH specifies the path to the directory containing a '
            'user_config.py file (optional)\n'
            '\t-update_mappings:BOOL if mappings should first be updated '
            'against online sources (defaults to True)\n'
        )
        info = super(SMVKInfo, cls).main(usage=usage, *args)
        if info:
            info.log.write_w_timestamp('...Make info finished\n')
            pywikibot.output(info.log.close_and_confirm())


class SMVKItem(object):
    """Store metadata and methods for a single media file."""

    def __init__(self, initial_data, archive_data, smvk_info):
        """
        Create a SMVKItem item from a dict where each key is an attribute.

        :param initial_data: dict of data to set up item with
        :param smvk_info: the SMVKInfo instance creating this SMVKItem
        """
        for key, value in initial_data.items():
            setattr(self, key, value)

        self.problems = []  # any reasons for not uploading the image
        self.content_cats = set()  # content relevant categories without prefix
        self.meta_cats = set()  # meta/maintenance proto categories
        self.needs_place_cat = True  # if item needs categorisation by place
        self.smvk_info = smvk_info
        self.log = smvk_info.log
        self.commons = smvk_info.commons
        self.archive_cards = archive_data
        self.geo_data = self.get_geo_data()
        self.museum = self.museum_obj.split('/')[0]

        # called at init to check for blockers or prevent multiple runs
        self.date_text = self.get_date_text()
        self.license_text = self.get_license_text()
        self.description_clean = self.get_clean_description()

    def is_photo(self):
        """
        Determine if image is a photo rather than other type of artwork.

        Broken out to systematically use same logic.
        """
        if self.creator:
            return False
        return True

    def get_clean_description(self):
        """Remove meta info from description string."""
        desc = self.description_sv.strip()
        if not desc:
            self.problems.append('There was no description')
            return

        desc = utils.description_cleaner(desc)

        # log problem if end result is empty
        if not desc.strip('0123456789,.- ?'):
            self.problems.append(
                'Nothing could be salvaged of the description')
            return

        # strip whitespace and trailing , or .
        return desc.rstrip(' ,.')

    def get_title_description(self):
        """
        Construct an appropriate description for a filename.

        The location part prioritises ort and region over depicted_places and
        other_geo as these are cleaner. Land is always included. Uncertain
        entries are filterd out.
        out.
        """
        txt = self.description_clean
        geo = (
            utils.clean_uncertain(self.ort) or
            utils.clean_uncertain(self.region) or
            utils.clean_uncertain(self.depicted_places) or
            utils.clean_uncertain(self.other_geo)
        )
        land = (
            utils.clean_uncertain(self.land) or
            utils.clean_uncertain(self.depicted_land)
        )
        if geo or land:
            txt += '. {}'.format(', '.join(geo))
            if geo and land:
                if land in txt:  # avoid duplicated info
                    return txt
                txt += '. '
            txt += land
        return txt

    def get_original_description(self, wrap=False):
        """
        Given an item get an appropriate original description.

        :param wrap: whether to wrap the results in an {{Information field}}.
        """
        txt = self.description_sv
        raw_geo = self.geo_data.get('raw')
        if any(raw_geo.values()):
            places = []
            for k, v in raw_geo.items():
                if v:
                    places.append('{} ({})'.format(
                        ', '.join(v), GEO_LABELS.get(k).get('sv')))
            txt += utils.format_description_row('Plats', places, delimiter=';')
        if self.depicted_persons:
            txt += utils.format_description_row(
                'Avbildade personer', self.depicted_persons)
        if self.ethnic or self.ethnic_old:
            ethnicities = []
            if self.ethnic:
                ethnicities.append(', '.join(self.ethnic))
            if self.ethnic_old:
                ethnic_old = ', '.join(self.ethnic_old)
                if ethnicities:
                    ethnic_old += ' (tidigare)'
                ethnicities.append(ethnic_old)
            txt += utils.format_description_row(
                'Etnisk grupp', ethnicities, delimiter=';')
        if self.motivord:
            txt += utils.format_description_row('Motivord', self.motivord)
        if self.sokord:
            txt += utils.format_description_row('Sökord', self.sokord)

        if wrap:
            return '{{SMVK description|1=%s}}' % txt.strip()
        return txt.strip()

    def get_id_link(self):
        """Create the id link template."""
        return self.smvk_info.build_link_template(
            self.museum_obj, self.db_id, self.photo_id)

    def get_archive_id_link(self, card_data):
        """Create the id link template for an archive card."""
        return self.smvk_info.build_link_template(
            card_data.get('museum_obj'),
            card_data.get('db_id'),
            card_data.get('label'))

    def get_museum_link(self):
        """Return the Wikidata linked museum."""
        mapping = self.smvk_info.mappings.get('museums')
        qid = mapping.get(self.museum).get('item')
        return '{{item|%s}}' % qid

    def get_source(self):
        """
        Produce a linked source statement.

        Does not include the original filename as multiple versions of the
        file exists and these may have been relabled before delivery.
        """
        mapping = self.smvk_info.mappings.get('museums')
        museum_code = mapping.get(self.museum).get('code')
        return '{{SMVK cooperation project|museum=%s}}' % museum_code

    def get_event_data(self, strict=True):
        """
        Return data about the event.

        :param strict: Whether to discard uncertain entries.
        """
        event = utils.clean_uncertain(self.event, keep=not strict)
        return self.smvk_info.mappings.get('expeditions').get(event, {})

    def get_ethnic_data(self, strict=True):
        """
        Return data about ethnic groups.

        :param strict: Whether to discard uncertain entries.
        """
        ethnic = self.ethnic or self.ethnic_old
        data = []
        ethnicities = utils.clean_uncertain(ethnic, keep=not strict)
        if not ethnicities:
            return data
        mapping = self.smvk_info.mappings.get('ethnic')
        for ethnicity in ethnicities:
            data.append(mapping.get(ethnicity.casefold()) or
                        {'name': ethnicity.casefold()})
        return data

    def get_description(self, with_depicted=False):
        """
        Given an item get an appropriate description in Swedish and English.

        :param with_depicted: whether to also include depicted data
        """
        sv_desc = '{}. '.format(self.description_clean)
        en_desc = ('{}. '.format(self.description_en.strip().rstrip(' .,'))
                   ).lstrip(' .')

        ethnic_data = self.get_ethnic_data(strict=False)
        if ethnic_data:
            sv_desc += '{}. '.format(', '.join(
                [ethnicity.get('name').title() for ethnicity in ethnic_data]))
            qids = list(filter(None, [ethnicity.get('wikidata')
                                      for ethnicity in ethnic_data]))
            if qids:
                en_desc += '{}. '.format(', '.join(
                    ['{{item|%s}}' % qid for qid in qids]))

        sv_desc += ('{}. '.format(self.get_geo_string())).lstrip(' .')

        event_data = self.get_event_data(strict=False)
        if event_data:
            uncertain = False
            if not self.get_event_data():
                uncertain = True
            sv_desc += '{}{}. '.format(event_data.get('sv'),
                                       ' (troligen)' if uncertain else '')
            en_desc += '{}{}. '.format(event_data.get('en'),
                                       ' (probably)' if uncertain else '')

        desc = '{{sv|%s}}\n{{en|%s}}' % (sv_desc, en_desc)
        if with_depicted:
            desc += '\n{}'.format(self.get_depicted_place(wrap=True))

        return desc.strip()

    def get_geo_string(self):
        """Return a string of the original geodata."""
        txt = ''
        label_data = self.geo_data.get('labels')
        for labels in label_data.values():
            if labels:
                txt += '{}; '.format(', '.join(labels))
        return txt.strip(' ;')

    def get_depicted_place(self, wrap=False):
        """
        Format a depicted place statement.

        Output other places values until the first one mapped to Wikidata is
        encountered. All values in a type are always outputted.

        :param wrap: whether to wrap the result in {{depicted place}}.
        """
        wikidata = self.geo_data.get('wd')
        label_data = self.geo_data.get('labels')
        depicted = []
        for geo_type, labels in label_data.items():
            depicted_type = []
            found_wd = False
            if not labels:
                continue
            for geo_entry in labels:
                if geo_entry in wikidata.get(geo_type):
                    depicted_type.append(
                        '{{item|%s}}' % wikidata.get(geo_type).get(geo_entry))
                    found_wd = True
                else:
                    depicted_type.append(geo_entry.strip())
            clean_type = GEO_LABELS.get(geo_type).get('en')
            depicted.append('{val} ({key})'.format(
                key=helpers.italicize(clean_type),
                val=', '.join(depicted_type)))
            if found_wd:
                break

        if not depicted:
            return ', '.join(self.geo_data.get('other'))
        depicted_str = '; '.join(depicted)
        if not wrap:
            return depicted_str
        else:
            return '{{depicted place|%s}}' % depicted_str

    def get_geo_data(self):
        """
        Find commonscat and wikidata entries for each available place level.

        Returns an dict with the most specific wikidata entry and any matching
        commonscats in decreasing order of relevance.

        If any 'other_geo' value is matched the wikidata ids are returned and
        the categories are added as content_cats.

        Uncertain entries are filtered out from everything except raw.
        """
        wikidata = OrderedDict()
        commonscats = OrderedDict()
        labels = OrderedDict()
        raw = OrderedDict()
        for geo_type in GEO_ORDER:
            # all except country are lists so handle all as lists
            wikidata_type = {}
            commonscats_type = []
            labels_type = []
            geo_entries_raw = []
            if getattr(self, geo_type):  # country otherwise makes ['']
                geo_entries_raw = common.listify(getattr(self, geo_type))
            geo_entries = utils.clean_uncertain(geo_entries_raw)
            for geo_entry in geo_entries:
                label = geo_entry.strip()
                mapping = self.smvk_info.mapped_and_wikidata(
                    geo_entry, self.smvk_info.mappings['places'])
                if mapping.get('category'):
                    commonscats_type += mapping.get('category')  # a list
                if mapping.get('wikidata'):
                    wikidata_type[label] = mapping.get('wikidata')
                labels_type.append(label)
            wikidata[geo_type] = wikidata_type
            commonscats[geo_type] = list(set(commonscats_type))
            labels[geo_type] = labels_type
            raw[geo_type] = geo_entries_raw

        # assume country is always mapped and either land OR depicted land used
        if len(list(filter(None, commonscats.values()))) <= 1:
            # just knowing country is pretty bad
            self.meta_cats.add('needing categorisation (place)')

        # add other_geo to raw
        raw['other_geo'] = self.other_geo

        return {
            'wd': wikidata,
            'commonscats': commonscats,
            'labels': labels,
            'raw': raw,
            'other': utils.clean_uncertain(self.other_geo)
        }

    def get_references(self):
        """Return a combination of the two reference types."""
        refs = set()
        if self.reference_source:
            refs.add(self.reference_source)
        if self.reference_published:
            refs.update(self.reference_published)  # list
        if len(refs) == 1:
            return refs.pop()
        return '* {}'.format('\n* '.join(refs)).strip().rstrip('*')

    def get_person_data(self, name):
        """
        Return the mapped data for a person, if any exists.

        :param name: unflipped name
        """
        person = helpers.flip_name(name)
        mapping = self.smvk_info.mapped_and_wikidata(
            person, self.smvk_info.mappings['people'])
        return mapping or {'name': person}

    def get_creator_name(self, data=False):
        """Return correctly formated creator values in wikitext."""
        uncertain = False
        person_data = self.get_creator_data()
        if not person_data:
            # check if it was filtered out due to uncertainty
            person_data = self.get_creator_data(strict=False)
            uncertain = True

        if not person_data:
            return '{{unknown|author}}'

        txt = ''
        if uncertain:
            txt = '{{Probably}} '
        if person_data.get('creator'):
            txt += '{{Creator:%s}}' % person_data.get('creator')
        elif person_data.get('wikidata'):
            txt += '{{item|%s}}' % person_data.get('wikidata')
        else:
            txt += person_data.get('name')
        return txt

    def get_creator_data(self, strict=True):
        """
        Return the mapped person data for the creator(s).

        :param strict: Whether to discard uncertain entries.
        """
        person = self.creator or self.photographer  # don't support both
        person = utils.clean_uncertain(person, keep=not strict)
        if person:
            return self.get_person_data(person)
        return {}

    def get_depicted_person(self, wrap=False):
        """
        Format a depicted person statement.

        The result is always wrapped in a {{depicted person}} template.
        People are added either by their wikidata id or by their name.
        Note that the template itself only supports up to 5 people

        :param wrap: whether to set the 'information field' style, wrapping
            the result in an {{information field}}.
        """
        if not self.depicted_persons:
            return ''

        formatted_people = []
        for person in utils.clean_uncertain(self.depicted_persons, keep=True):
            person_data = self.get_person_data(person)
            if person_data.get('category'):
                self.content_cats.update(person_data.get('category'))
            formatted_people.append(
                person_data.get('wikidata') or person_data.get('name'))

        style = '|style=information field' if wrap else ''
        return u'{{depicted person|%s%s}} ' % (
            '|'.join(formatted_people), style)

    def make_place_category(self):
        """
        Add the most specific geo categories.

        Loops over the geo_type from most to least specific, adding all
        matching categoires for the geo_type where the first match is found.
        """
        found_cat = False
        for geo_type, geo_cats in self.geo_data.get('commonscats').items():
            for geo_cat in geo_cats:
                if self.smvk_info.category_exists(geo_cat):
                    self.content_cats.add(geo_cat)
                    found_cat = True
            if found_cat:
                return True

        # no geo cats found
        self.meta_cats.add('needing categorisation (place)')
        return False

    def make_event_categories(self):
        """Construct categories from the event data."""
        event_data = self.get_event_data()  # filter out uncertain entries
        if event_data:
            self.content_cats.add(event_data.get('cat'))
        return event_data.get('cat')  # to allow access to these in make_meta

    def make_ethnic_categories(self):
        """Construct categories from the ethnicity data."""
        ethnic_data = self.get_ethnic_data()  # filters out uncertain
        for ethnicity in ethnic_data:
            if ethnicity.get('category'):
                self.content_cats.update(ethnicity.get('category'))

    def make_item_keyword_categories(self):
        """Construct categories from the item keyword values."""
        all_keywords = set()
        if self.motivord:
            all_keywords.update([keyword.casefold() for keyword in
                                 utils.clean_uncertain(self.motivord)])
        if self.sokord:
            all_keywords.update([keyword.casefold() for keyword in
                                 utils.clean_uncertain(self.sokord)])
        keyword_map = self.smvk_info.mappings.get('keywords')

        for keyword in all_keywords:
            if keyword not in keyword_map:
                continue
            for cat in keyword_map[keyword]:
                match_on_first = True
                found_testcat = False
                for place_cats in self.geo_data.get('commonscats').values():
                    if not place_cats:
                        continue
                    found_testcat = any(
                        [self.try_cat_patterns(cat, place_cat, match_on_first)
                         for place_cat in place_cats])
                    if found_testcat:
                        break
                    match_on_first = False
                if not found_testcat and self.smvk_info.category_exists(cat):
                    self.content_cats.add(cat)

    def try_cat_patterns(self, base_cat, place_cat, match_on_first):
        """Test various combinations to construct a geographic subcategory."""
        test_cat_patterns = ('{cat} in {place}', '{cat} of {place}')
        for pattern in test_cat_patterns:
            test_cat = pattern.format(cat=base_cat, place=place_cat)
            if self.smvk_info.category_exists(test_cat):
                self.content_cats.add(test_cat)
                if match_on_first:
                    self.needs_place_cat = False
                return True
        return False

    def get_license_text(self):
        """Format a license template."""
        if self.license not in ('PD', 'cc0'):
            raise common.MyError(
                'A non-supported license was encountered: {}'.format(
                    self.license))

        # CC0 is straight forward
        if self.license == 'cc0':
            return '{{CC0}}'

        # PD - identify creator and image type (photo/artwork)
        # creator death year > 70
        #     {{PD-old-auto}}
        # photo, creator known and image date < 1969
        #     {{PD-Sweden-photo}}
        creator = self.get_creator_data()  # skips any uncertain
        if creator:
            death_year = creator.get('death_year')
            creation_year = utils.get_last_year(self.date_text)
            if death_year and death_year < self.smvk_info.pd_year:
                return '{{PD-old-auto|deathyear=%s}}' % death_year
            elif death_year and not self.is_photo():
                self.problems.append(
                    'The creator death year ({}) is not late enough for PD '
                    'and this does not seem to be a photo.'.format(
                        death_year))
            elif self.is_photo() and creation_year and creation_year < 1969:
                return '{{PD-Sweden-photo}}'
            else:
                self.problems.append(
                    'Could not determine why this image by {} is PD.'.format(
                        creator.get('name')))
        else:
            # cannot default to PD-Sweden-photo since creator need not be
            # Swedish. Cannot default to PD-anon-70 since date of first
            # publication is not known.
            self.problems.append(
                'The creator is unknown so PD status cannot be verified')

    # do not run self.date through util.clean_uncertain(),
    # helpers.std_data_range handles any comments
    def get_date_text(self):
        """Format a creation date statement."""
        if self.date:
            clean_date = '|'.join(self.date).replace('[', '').replace(']', '')
            date_text = helpers.std_date_range(clean_date, range_delimiter='|')

            if not date_text:
                self.meta_cats.add('needing date formatting')
            else:
                return date_text
        elif self.get_event_data():
            event_date = self.get_event_data().get('date')
            if len(event_date) == 2:
                return '{{other date|-|%s|%s}}' % tuple(event_date)
            else:
                return event_date[0]
        return '{{unknown|date}}'

    def get_notes(self):
        """
        Format a note statement.

        The note statement combines any archive cards and any mentions of this
        image in other databases.
        """
        txt = ''
        if self.archive_cards:
            txt += 'Related archive card(s): {}'.format(
                ', '.join([self.get_archive_id_link(card)
                           for card in self.archive_cards]))
        if self.ext_id:
            txt += '\nId in other archives: {}'.format(
                ', '.join([utils.parse_external_ids(id)
                           for id in self.ext_id]))
        return txt


if __name__ == "__main__":
    SMVKInfo.main()
