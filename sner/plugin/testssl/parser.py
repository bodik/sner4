# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent testssl
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from pprint import pprint
from zipfile import ZipFile

from sner.lib import file_from_zip
from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """testssl parser"""

    ARCHIVE_PATHS = r'output\-[0-9]+\.json'
    FINDINGS_IGNORE = ['OK', 'INFO']

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()

        with ZipFile(path) as fzip:
            for fname in filter(lambda x: re.match(cls.ARCHIVE_PATHS, x), fzip.namelist()):
                pidb = cls._parse_data(file_from_zip(path, fname).decode('utf-8'), pidb)

        return pidb

    @classmethod
    def _parse_data(cls, data, pidb):
        """parse raw string data"""

        json_data = json.loads(data)
        if not isinstance(json_data['scanTime'], int):  # pragma: no cover
            return pidb

        result = json_data['scanResult'][0]
        host_address = result['targetHost']
        service_port = int(result['port'])
        service_proto = 'tcp'

        note_data = {
            'output': data,
            'data': {},
            'findings': defaultdict(list)
        }

        for section_name, section_data in result.items():
            if isinstance(section_data, list):
                # pop findings for section
                for finding in section_data:
                    if finding['id'] == 'cert':
                        # rewrap certificate data
                        tmp = finding['finding'].split(' ')
                        tmp = ' '.join(tmp[:2]) + '\n' + '\n'.join(tmp[2:-2]) + '\n' + ' '.join(tmp[-2:])
                        # parse as auror tool
                        try:
                            note_data['cert_txt'] = subprocess.run(
                                ['openssl', 'x509', '-text', '-noout'],
                                input=tmp, check=True, capture_output=True, text=True
                            ).stdout
                        except subprocess.CalledProcessError as exc:  # pragma: no cover
                            note_data['cert_txt'] = str(exc)

                    if finding['severity'] not in cls.FINDINGS_IGNORE:
                        note_data['findings'][section_name].append(finding)
            else:
                # pop scalar data
                note_data['data'][section_name] = section_data

        pidb.upsert_note(host_address, 'testssl', service_proto, service_port, data=json.dumps(note_data))

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
