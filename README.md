## SMVK-import
*SMVK-import* is a collection of scripts and tools for the batch upload of
images from the collections of The National Museums of World Culture (*Statens museer för världskultur*).

As a starting point you are expected to have two a correctly formatted csv
files (main data + archive cards) provided by the agency.

* `smvk_mergeFiles` is used to merge two csv file pairs from different museums
  prior to further crunching.
* `smvk_updateMappings` is used to parse the csv data and create new mapping
  tables for upload to Wikimedia Commons.
* `smvk_makeInfo` is used to parse the csv and combine it with the mapped data
  to construct a data file suitable for upload using `uploader.py`.

Instructions for how to use `uploader.py` can be found in [lokal-profil/BatchUploadTools](https://github.com/lokal-profil/BatchUploadTools).

### Installation
If `pip -r requirements.txt` does not work correctly you might have to add
the `--process-dependency-links` flag to ensure you get the right version
of [Pywikibot](https://github.com/wikimedia/pywikibot-core/) and
[lokal-profil/BatchUploadTools](https://github.com/lokal-profil/BatchUploadTools).
