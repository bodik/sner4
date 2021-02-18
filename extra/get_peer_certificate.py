#!/usr/bin/env python3
"""helper used for ad-hoc certificate pinning"""

from argparse import ArgumentParser
from ssl import get_server_certificate


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('host', help='hostname or address')
    parser.add_argument('--port', type=int, default=443, required=False, help='peer port')
    args = parser.parse_args()

    cert = get_server_certificate((args.host, args.port))
    print(cert.strip())


if __name__ == '__main__':
    main()
