#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Small parser utils for smvk."""
import pywikibot


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
