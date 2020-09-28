#/usr/bin/env python

import logging
import subprocess
from argparse import ArgumentParser
from pathlib import Path

logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)

PORTLIST_FILE = 'scada.portlist'

def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)

    portlist = []
    for item in (Path(__file__).parent / PORTLIST_FILE).read_text().splitlines():
        if item.startswith('#'):
            continue
        elif item.isnumeric():
            portlist.append(int(item))
        elif '-' in item:
            start, end = item.split('-')
            for i in range(int(start), int(end)):
                portlist.append(i)
        else:
            logging.warn(f'invalid item {item}')
    logging.debug(portlist)

    subprocess.run(['bin/server', 'storage', 'service-list', '--filter', f'Service.port in {portlist}'])


if __name__ == '__main__':
    main()
