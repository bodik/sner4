# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared functions
"""

import os
import signal
from contextlib import contextmanager
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
        with open(filename, 'r', encoding='utf-8') as ftmp:
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


def format_host_address(value):
    """format ipv4 vs ipv6 address to string"""
    return value if ':' not in value else f'[{value}]'


class TerminateContextMixin:  # pylint: disable=too-few-public-methods
    """terminate context mixin"""

    @contextmanager
    def terminate_context(self):
        """terminate context manager; should restore handlers despite of underlying code exceptions"""

        self.original_signal_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, self.terminate)
        self.original_signal_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self.terminate)
        try:
            yield
        finally:
            signal.signal(signal.SIGINT, self.original_signal_handlers[signal.SIGINT])
            signal.signal(signal.SIGTERM, self.original_signal_handlers[signal.SIGTERM])
