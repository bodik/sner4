#!/usr/bin/python3
"""service-list by ports from file"""

import logging
import subprocess
from argparse import ArgumentParser
from pathlib import Path

logger = logging.getLogger()  # pylint: disable=invalid-name
logger.addHandler(logging.StreamHandler())


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('portfile')
    args, unk_args = parser.parse_known_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.debug('args: %s', args)
    logger.debug('unk_args: %s', unk_args)

    portlist = []
    for item in Path(args.portfile).read_text().splitlines():
        if item.startswith('#'):
            continue

        if item.isnumeric():
            portlist.append(int(item))
        elif '-' in item:
            start, end = item.split('-')
            for port in range(int(start), int(end)):
                portlist.append(port)
        else:
            logging.error('invalid item %s', item)

    subprocess.run(['bin/server', 'storage', 'service-list', '--filter', f'Service.port in {portlist}'] + unk_args, check=True)


if __name__ == '__main__':
    main()
