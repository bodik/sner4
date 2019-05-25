"""agents tests shared functions"""

from zipfile import ZipFile


def file_from_zip(zippath, filename):
    """exctract filename data from zipfile"""

    with ZipFile(zippath) as ftmp_zip:
        with ftmp_zip.open(filename) as ftmp:
            return ftmp.read()
