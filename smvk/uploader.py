#!/usr/bin/python
# -*- coding: utf-8  -*-
"""Tool for uploading a single or multiple files from disc or url."""
import batchupload.uploader as uploader


def main(*arguments):
    """Redirect to real function."""
    uploader.main(*arguments)


if __name__ == "__main__":
    main()
