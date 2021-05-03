#!/usr/bin/env python3

from sner.server.app import create_app
from sner.server.storage.models import Host


with create_app().app_context():
    for host in Host.query.all():
        print(host)
