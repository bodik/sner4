# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller portmap tests
"""

from http import HTTPStatus

from flask import url_for


def test_portmap_route(cl_operator, test_service):
    """portmap route test"""

    response = cl_operator.get(url_for('visuals.portmap_route'))
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//a[@class="portmap_item" and @data-port="%d"]' % test_service.port)

    response = cl_operator.get(url_for('visuals.portmap_route', filter='Service.state=="%s"' % test_service.state))
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//a[@class="portmap_item" and @data-port="%d"]' % test_service.port)


def test_portmap_portstat_route(cl_operator, test_service):
    """portmap portstat route test"""

    response = cl_operator.get(url_for('visuals.portmap_portstat_route', port=test_service.port))
    assert response.status_code == HTTPStatus.OK

    assert response.lxml.xpath('//td/a[text()="%s"]' % test_service.info)
