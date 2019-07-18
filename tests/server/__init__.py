# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner.server tests
"""

from flask import url_for


def get_csrf_token(client):
    """fetch index and parse csrf token"""

    response = client.get(url_for('index_route'))
    return response.lxml.xpath('//meta[@name="csrf-token"]/@content')[0]


class DummyPostData(dict):
    """used for testing edge-cases on forms processing"""

    def getlist(self, key):
        """accessor; taken from wtforms testsuite"""

        v = self[key]  # pylint: disable=invalid-name
        if not isinstance(v, (list, tuple)):
            v = [v]  # pylint: disable=invalid-name
        return v
