# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared functions
"""

import os
from zipfile import ZipFile

import magic
import yaml


def get_dotted(data, path):
    """access nested dict by dotted helper"""

    parts = path.split('.')
    if len(parts) == 1:
        return data.get(parts[0])
    if (parts[0] in data) and isinstance(data[parts[0]], dict):
        return get_dotted(data[parts[0]], '.'.join(parts[1:]))
    return None


def load_yaml(filename):
    """load yaml from file, silence file not found"""

    if filename and os.path.exists(filename):
        with open(filename, 'r') as ftmp:
            return yaml.safe_load(ftmp.read())
    return {}


def is_zip(path):
    """detect if path is zip archive"""
    return magic.detect_from_filename(path).mime_type == 'application/zip'


def file_from_zip(zippath, filename):
    """exctract filename data from zipfile"""

    with ZipFile(zippath) as ftmp_zip:
        with ftmp_zip.open(filename) as ftmp:
            return ftmp.read()
