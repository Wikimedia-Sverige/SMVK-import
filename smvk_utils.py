#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Small parser utils for smvk."""
import re
import pywikibot
import batchupload.common as common
import batchupload.helpers as helpers


def parse_external_id(ext_id):
    """Match an external id to a Commons formating template."""
    if ext_id.startswith('gnm/'):
        return gnm_parser(ext_id)
    elif ext_id.startswith('SMVK'):  # same image in use in a sister collection
        return smvk_parser(ext_id)

    # if not caught by any of the above
    pywikibot.warning('{} is not a recognized external id'.format(ext_id))


def smvk_parser(ext_id):
    """Parser for SMVK identifiers."""
    # Not as sensitive as build_link_template nor is it validated
    museum, type, id = ext_id.split('/', 2)
    prefix = ''
    if museum != 'SMVK-MM':  # MM has prefix as part of id
        prefix = '|{}'.format(type)
    return '{{%s-link%s|%s}}' % (museum, prefix, id)


def gnm_parser(ext_id):
    """Parser for Gothenburgh Natural Museum identifiers."""
    if not ext_id.startswith('gnm/photo/GNM'):
        pywikibot.warning(
            'The GNM parser needs to be extended to handle {}'.format(ext_id))
    return '{{GNM-link|%s}}' % ext_id[len('gnm/photo/GNM'):]


# consider movingto BatchUploadTools.common
def relabel_inner_dicts(obj, key_map):
    """Update the keys of all dicts in a dict."""
    for inner in obj.values():
        for old_key, new_key in key_map.items():
            inner[new_key] = inner.pop(old_key)
    return obj


def invert_dict(old_dict):
    """Invert a dict where each value is itself hashable."""
    # note that OrderedDict gets converted to dict
    return {v: k for k, v in old_dict.items()}


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
        helpers.italicize(label),
        delimiter.join(common.listify(value)))


def replace_repeat_character(text, char_1, target, delimiter, char_2=None):
    """
    Replace two characters by a single one.

    Replaces them even if separated by space or delimiter. Also merges any
    adjacent delimiters.

    If char_2 is not provided then it is assumed that char_1 is repeated
    """
    char_2 = char_2 or char_1
    patterns = (
        char_1 + char_2,
        char_1 + delimiter + char_2,
        char_1 + ' ' + char_2)

    text = text.replace(delimiter * 2, delimiter)
    while any(text.find(pattern) > 0 for pattern in patterns):
        for pattern in patterns:
            text = text.replace(pattern, target + delimiter)
        text = text.replace(delimiter + ' ', delimiter)
        text = text.replace(delimiter * 2, delimiter)
    return text


def description_cleaner(text, structured=False):
    """
    Attempt a cleanup of SMVK descriptions.

    The descriptions contain a lot of info which is more of internal notes
    character. This method contains an ugly list of such strings and attempts
    to get rid of them.

    Outsourced to the utils file because it is ugly.

    :param structured: if internal structure should be kept to facilitate
        diffs.
    """
    delimiter = '¤'
    bad_endings = (  # anything found after one of these should be removed
        'Publ. Kaudern',
        'Publ. Walter Kaudern',
        'Publ. W. Kaudern',
        'Publ. W.Kaudern',
        'Publ. Kandun',
        'Publ. Nordenskiöld:',
        'Publ.: ',
        'publicera: ',
        'Publicerad: ',
        'Se Kaudern: ',
        'Se Walter Kaudern:',
        'Se W. Kaudern:',
        'Se W.Kaudern:',
        'Se Linell & Kaudern:',
        'Se Nordenskiöld:',
        'Se Erland Nordenskiöld:',
        'Jämför Nordenskiöld:',
        'Walter Kaudern: I Celebes obygder',
        'W. Kaudern: I Celebes obygder',
        'W.Kaudern: I Celebes obygder.',
        'W. Kaudern:" I Celebes obygder"',
        'W. Kaudern: Ethnographical Stud',
        'W. Kaudern: Structures and settlements',
        'W. Kaudern: På Madagaskar.',
        'Nordeskiiöld: Indianerna på Panamanäset',
        'Jfr. bildark',
        'Jfr. bildnr.',
        'Jfr. bindnr.',
        'Jfr. bild',
        'Jfr bild',
        'Jämför bild',
        'Bildark: ',
        'Erh: gm köp av',
        'Erh: gm. köp av',
        'Erh.: gm köp av',
        'Erh.: gm. köp av',
        'Erh. gm. köp av',
        'erhållen gm. köp av',
        'Erhållet genom köp av',
        'Bilden erhållen genom köp av',
        'Foto erhållet av ',
        'Fotot erhållit ',
        'Neg.: ',
        # 'Negnr',
        # 'Neg.nr',
        'Foto av: ',
        'Foto taget av ',
        # 'Fotograf: ',
        'Först. eft.'
    )
    bad_starts = (  # anything found before one of these should be removed
        'Motiv [Gegenstand der Aufnahme]:',
        'Motiv [Gegenstand der Aufnahmne]:',
        'Motiv/Gegenstand der Aufnahme:',
        'Motiv: ',
        'Gegenstand der Aufnahme',
    )
    bad_middle = (  # these should be removed wherever they are found
        '(negativkuvert)',
        '(negativpåse)',
        '(Katalogkort)',
        '(katalogkort)',
        '(Katolkort)',
        '(glasplåt)',
        '(general katalog)'
        '(?)'
    )
    # clean out any Datum: ... . but beware of . in abbrev.
    # clean out any Ort: ... . but beware of . in abbrev.
    # flag odugl.

    for test in bad_endings:
        if text.find(test) >= 0:
            text = text[:text.find(test)]
    for test in bad_starts:
        if text.find(test) >= 0:
            text = text[text.find(test) + len(test):]

    # remove blocks inside kept text
    for test in bad_middle:
        if text.find(test) >= 0:
            start = text.find(test)
            end = start + len(test)
            text = text[:start].rstrip() + delimiter + text[end + 1:].lstrip()

    # clean out any [...], there may be many
    while text.find('[') >= 0:
        start = text.find('[')
        end = text.find(']', start)
        if end < 0:
            break
        text = text[:start].rstrip() + delimiter + text[end + 1:].lstrip()

    # remove repeats, even if interspersed with delimiters
    repeats = (' ', ',', '.')
    for char in repeats:
        text = replace_repeat_character(text, char, char, delimiter)
    # special case .,
    text = replace_repeat_character(text, '.', '.', delimiter, char_2=',')

    # merge any remaining removed blocks
    while text.find(delimiter * 2) > 0:
        text = text.replace(delimiter * 2, delimiter)
    # ignore any removed block in the end
    text = text.strip(delimiter)

    if structured:
        return text.split(delimiter)
    else:
        return text.replace(delimiter, ' ')


def clean_all_descriptions(filename):
    """
    Clean all descriptions in a file.

    Load a file with one description per row, clean each and output a visible
    diff for on-wiki consumption.
    """
    import os.path as path
    base, ext = path.splitext(filename)
    f_in = open(filename)
    f_out = open('{}_clean{}'.format(base, ext), 'w')

    intro = (
        'Preview of description cleanup for SMVK.\n'
        '{} text is discarded, <span style="color:blue">{}</span> text is '
        'kept, <span style="color:red">{}</span> indicates a description '
        'which was completely discarded.\n\n----\n\n'.format(
            helpers.bolden('Black'),
            helpers.bolden('blue'),
            helpers.bolden('red')))
    f_out.write(intro)

    for l in f_in:
        if not l.strip():
            f_out.write('* {}'.format(l))
            continue
        cleaned = description_cleaner(l, structured=True)
        if not any(block.strip() for block in cleaned):
            f_out.write('* <span style="color:red">{}</span>\n'.format(
                l.rstrip()))
        else:
            end = 0
            clean_l = l
            for block in cleaned:
                block = block.strip()
                start = clean_l.find(block, end)
                end = start + len(block)
                clean_l = '{}<span style="color:blue">{}</span>{}'.format(
                    clean_l[:start], block, clean_l[end:])
                end += len('<span style="color:blue"></span>')
            f_out.write('* {}'.format(clean_l))
    f_in.close()
    f_out.close()
