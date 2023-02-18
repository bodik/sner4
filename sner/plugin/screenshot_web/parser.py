# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent screenshot web
"""

import json
import re
import sys
from base64 import b64encode
from datetime import datetime
from pprint import pprint

from sner.agent.modules import SERVICE_TARGET_REGEXP
from sner.lib import file_from_zip
from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """screenshot_web parser"""

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()
        results = json.loads(file_from_zip(path, 'results.json'))
        for filename, target in results.items():
            service_str, url = target['target'].split(' ', maxsplit=1)

            if mtmp := re.match(SERVICE_TARGET_REGEXP, service_str):
                pidb.upsert_note(
                    mtmp.group('host'),
                    'screenshot_web',
                    service_proto=mtmp.group('proto'),
                    service_port=mtmp.group('port'),
                    via_target=url,
                    data=json.dumps({'url': url, 'img': b64encode(file_from_zip(path, filename)).decode()}),
                    import_time=datetime.fromisoformat(target['timestamp'])
                )

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
