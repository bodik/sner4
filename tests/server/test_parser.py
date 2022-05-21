# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
test parser api
"""

from sner.server.parser import ParsedItemsDb


def test_upsert_host():
    """test upsert host"""

    pidb = ParsedItemsDb()
    pidb.upsert_host(address='192.0.2.1')
    pidb.upsert_host(address='192.0.2.1', hostname='xxx')

    assert len(pidb.hosts) == 1


def test_upsert_service():
    """test upsert service"""

    pidb = ParsedItemsDb()
    pidb.upsert_service(host_address='192.0.2.1', proto='tcp', port=21)
    pidb.upsert_service(host_address='192.0.2.2', proto='udp', port=88)
    pidb.upsert_service(host_address='192.0.2.2', proto='udp', port=88, name='dns')

    assert len(pidb.hosts) == 2
    assert len(pidb.services) == 2


def test_upsert_vuln():
    """test upsert vuln"""

    pidb = ParsedItemsDb()
    pidb.upsert_vuln('192.0.2.1', 'dns axfr', 'testxtype')  # vuln1
    pidb.upsert_vuln('192.0.2.2', 'anonymous ftp', 'testxtype', service_proto='tcp', service_port=21)  # vuln2
    pidb.upsert_vuln('192.0.2.3', 'sqli', 'testxtype', service_proto='tcp', service_port=80, via_target='webhost1', data='data1')  # vuln3
    pidb.upsert_vuln('192.0.2.3', 'sqli', 'testxtype', service_proto='tcp', service_port=80, via_target='webhost1', data='data2')  # vuln3 update
    pidb.upsert_vuln('192.0.2.3', 'sqli', 'testxtype', service_proto='tcp', service_port=80, via_target='webhost2', data='data3')  # vuln4

    assert len(pidb.hosts) == 3
    assert len(pidb.services) == 2
    assert len(pidb.vulns) == 4


def test_upsert_note():
    """test upsert note"""

    pidb = ParsedItemsDb()

    pidb.upsert_note('192.0.2.1', 'testxtype', data='axfr data')
    pidb.upsert_note('192.0.2.2', 'anothertype', service_proto='tcp', service_port=11, data='data1')
    pidb.upsert_note('192.0.2.2', 'anothertype', service_proto='tcp', service_port=11, data='data2')

    assert len(pidb.hosts) == 2
    assert len(pidb.services) == 1
    assert len(pidb.notes) == 2
