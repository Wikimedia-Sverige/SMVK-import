#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Small parser utils for smvk."""
import re
import pywikibot
import batchupload.common as common
import batchupload.helpers as helpers


def parse_external_ids(ext_id):
    """Match an external id to a Commons formating template."""
    if ext_id.startswith('gnm/'):
        return gnm_parser(ext_id)

    # if not caught by any of the above
    pywikibot.warning('{} is not a recognized external id'.format(ext_id))


def gnm_parser(ext_id):
    """Parser for Gothenburgh Natural Museum identifiers."""
    if not ext_id.startswith('gnm/photo/GNM'):
        pywikibot.warning(
            'The GNM parser needs to be extended to handle {}'.format(ext_id))
    return '{{GNM-link|%s}}' % ext_id[len('gnm/photo/GNM'):]


def relabel_inner_dicts(obj, key_map):
    """Update the keys of all dicts in a dict."""
    for inner in obj.values():
        for old_key, new_key in key_map.items():
            inner[new_key] = inner.pop(old_key)
    return obj


def clean_uncertain(value, keep=False):
    """
    Handle uncertain values in the data.

    Process any value containing a '[?]' string.

    :param value: the value or list of values to process
    :param keep: whether to keep the clean value or discard it
    """
    was_list = isinstance(value, list)
    values = common.listify(value)
    new_list = []
    for val in values:
        if '[?]' in val:
            if keep:
                new_list.append(
                    val.replace('[?]', '').replace('  ', ' ').strip())
        else:
            new_list.append(val)

    # return in same format as original
    if not was_list:
        if not new_list:
            return ''
        return new_list[0]
    return new_list


def get_last_year(date_text):
    """Attempt to extract the last year in a wikitext date template."""
    hits = re.findall('\d\d\d\d', date_text)
    if hits:
        return int(hits[-1])


def format_description_row(label, value, delimiter=','):
    """Format a single description line."""
    delimiter = '{} '.format(delimiter)
    return '<br/>\n{}: {}'.format(
        helpers.italicize('label'),
        delimiter.join(common.listify(value)))


def description_cleaner(text):
    """
    Attempt a cleanup of SMVK descriptions.

    The descriptions contain a lot of info which is more of internal notes
    character. This method contains an ugly list of such strings and attempts
    to get rid of them.

    Outsourced to the utils file because it is ugly.
    """
    bad_endings = (  # anything found after one of these should be removed
        'W. Kaudern: I Celebes obygder',
        'W.Kaudern: I Celebes obygder.',
        'Walter Kaudern: I Celebes obygder',
        'W. Kaudern:" I Celebes obygder"',
        'W. Kaudern: Ethnographical Studies in Celebes',
        'W. Kaudern: På Madagaskar.',
        'Se Kaudern: ',
        'Se Walter Kaudern: ',
        'Se Linell & Kaudern: ',
        'Jfr. bildark',
        'Jfr. bildnr.',
        'Jfr. bindnr.',
        'Jfr. bild',
        'Bildark: ',
        # 'Neg.: ',
        'Foto av: ',
        # 'Fotograf: '
    )
    bad_starts = (
        'Motiv [Gegenstand der Aufnahme]: ',
        'Motiv/Gegenstand der Aufnahme: ',
        'Motiv: '
    )
    # om den innehåller "Gegenstand der Aufnahme", släpp allt före?
    # clean out any [...], there may be many
    # clean out any Datum: ... . but beware of . in abbrev.
    # clean out any Ort: ... . but beware of . in abbrev.
    # clean out (negativkuvert)
    # flag odugl.

    for test in bad_endings:
        if text.find(test) > 0:
            text = text[:text.find(test)]
    for test in bad_starts:
        if text.startswith(test):
            text = text[len(test):]

    return text
