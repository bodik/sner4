#!/usr/bin/python3

import logging
from argparse import ArgumentParser

from sqlalchemy_filters import apply_filters

from sner.server.app import create_app
from sner.server.extensions import db
from sner.server.sqlafilter import FILTER_PARSER
from sner.server.storage.models import Service


logger = logging.getLogger()  # pylint: disable=invalid-name
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--dry', action='store_true')
    parser.add_argument('action', choices=['add', 'remove'])
    parser.add_argument('tag')
    parser.add_argument('filter', nargs='?')
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.debug('args: %s', args)

    with create_app().app_context():
        query = Service.query
        if args.filter:
            query = apply_filters(query, FILTER_PARSER.parse(args.filter), do_auto_join=False)

        for service in query.all():
            logging.info(service)
            if args.action == 'add':
                service.tags = service.tags + [args.tag]
            elif args.action == 'remove':
                service.tags = service.tags - [args.tag]

        if not args.dry:
            db.session.commit()


if __name__ == '__main__':
    main()

