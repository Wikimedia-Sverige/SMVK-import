#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Broken out CSV parsing logic for SMVK data files."""
from collections import OrderedDict

import batchupload.csv_methods as csv_methods
import smvk_utils as utils

DELIMITER = '¤'
LIST_DELIMITER = '|'


def archive_metadata():
    """
    Maps column names in the archive data file to internal variables.

    This is the only place where the original column names should be
    mentioned.
    """
    columns = OrderedDict([
        ('Id', 'label'),
        ('Postnr', 'db_id'),
        ('Museum/objekt', 'museum_obj'),
        ('Fotonummer', 'photo_ids')])
    list_columns = ('Fotonummer', )
    key_column = 'Postnr'

    return columns, list_columns, key_column


def main_metadata():
    """
    Maps column names in the main data file to internal variables.

    This is the only place where the original column names should be
    mentioned.
    """
    columns = OrderedDict([
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
        ('Objekt, externt / samma som', 'ext_ids'),
        ('Etn, tidigare', 'ethnic_old'),
        ('Land, ursprung/brukad', 'depicted_land'),
        ('Region/Ort, ursprung', 'depicted_places'),
        ('Referens / källa', 'reference_source'),
        ('Media/Licens', 'license'),
        ('Museum/objekt', 'museum_obj')
    ])
    list_columns = (
        'Motivord', 'Sökord', 'Etnisk grupp', 'Personnamn, avbildad',
        'Region, fotograferad i', 'Ort, fotograferad i',
        'Geografiskt namn, annat', 'Fotodatum',
        'Objekt, externt / samma som', 'Region/Ort, ursprung',
        'Referens / Publicerad i')
    key_column = 'Fotonummer'

    return columns, list_columns, key_column


class CsvParser(object):
    """Rules and functionality for parsing the provided SMVK csv files."""

    def __init__(self, **options):
        self.delimiter = options.get('delimiter') or DELIMITER
        self.list_delimiter = options.get('list_delimiter') or LIST_DELIMITER
        self.main_metadata = main_metadata()
        self.archive_metadata = archive_metadata()

    def base_load_data(self, csv_file, metadata):
        """
        Load and parse the provided csv file.

        :param csv_file: the filename to load
        :param metadata: the metadata for the file
        """
        fields, list_columns, key_column = metadata

        expected_header = self.delimiter.join(fields.keys())
        raw_dict = csv_methods.csv_file_to_dict(
            csv_file, key_column, expected_header, lists=list_columns,
            delimiter=self.delimiter,
            list_delimiter=self.list_delimiter)

        return utils.relabel_inner_dicts(raw_dict, fields)

    def load_data(self, csv_file):
        """
        Load and parse the provided csv file.

        :param csv_file: the filename to load
        """
        return self.base_load_data(csv_file, self.main_metadata)

    def load_archive_data(self, csv_file, raw=False):
        """
        Load and parse the provided csv file for archive_cards.

        :param csv_file: the filename to load
        :param raw: whether to skip re-ordering the output
        """
        loaded_data = self.base_load_data(csv_file, self.archive_metadata)

        if raw:
            return loaded_data

        # re-order so photo_id is main key
        photo_id_dict = {}
        for k, v in loaded_data.items():
            for photo_id in v.get('photo_ids'):
                if photo_id not in photo_id_dict:
                    photo_id_dict[photo_id] = []
                photo_id_dict[photo_id].append(v)
        return photo_id_dict

    def base_output_data(self, data, metadata, filename):
        """
        Output data in the same format as it would be expected at load.

        :param data: the OrderedDict to output
        :param metadata: the metadata for the file
        :param filename: the output filename
        """
        fields, list_columns, key_column = metadata
        relabelled_data = utils.relabel_inner_dicts(
            data, utils.invert_dict(fields))
        header = self.delimiter.join(fields.keys())
        csv_methods.dict_to_csv_file(
            filename, relabelled_data, header, delimiter=self.delimiter,
            list_delimiter=self.list_delimiter)

    def output_data(self, data, filename):
        """
        Output the provided data as a csv file.

        :param data: the OrderedDict to output
        :param filename: the output filename
        """
        self.base_output_data(data, self.main_metadata, filename)

    def output_archive_data(self, data, filename):
        """
        Output the provided archive data as a csv file.

        :param data: the OrderedDict to output
        :param filename: the output filename
        """
        self.base_output_data(data, self.archive_metadata, filename)
