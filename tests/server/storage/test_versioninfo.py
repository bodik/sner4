# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.versioninfo_map functions tests
"""

from sner.server.storage.models import VersionInfo
from sner.server.storage.versioninfo import ExtractedVersion, RawMap, VersionInfoManager


def test_rawmap_aggregation():
    """test rawmap aggregation feature"""

    item = {
        'host_id': 1,
        'host_address': '127.0.0.1',
        'host_hostname': 'localhost.localdomain',
        'service_proto': 'tcp',
        'service_port': 1,
        'via_target': 'localhostx.localdomain',
        'product': 'dummy',
        'version': '0.1',
    }

    raw_map = RawMap()
    raw_map.add(**item, extra={'extra1': 'val1'})
    raw_map.add(**item, extra={'extra2': 'val2'})

    assert raw_map.values()[0]['extra'] == {'extra1': 'val1', 'extra2': 'val2'}


def test_versioninfomanager_rebuild(app, versioninfo_notes):  # pylint: disable=unused-argument
    """test versioninfo map rebuild"""

    VersionInfoManager.rebuild()

    assert VersionInfo.query.count() == 6
    assert VersionInfo.query.filter(VersionInfo.product == "apache httpd").one().version == "2.2.21"
    assert VersionInfo.query.filter(VersionInfo.product == "mod_ssl").one().version == "2.2.21"


def test_versioninfomanager_extract_version():
    """test VersionInfoManager.extract_version"""

    test_data = [
        # nmap.banner_dict
        {"in": "mod_perl/2.0.4", "out": ("mod_perl", "2.0.4")},
        {"in": "Perl/v5.10.1", "out": ("Perl", "5.10.1")},
        # nmap.http-generator
        {"in": "Backdrop CMS 1 (https://backdropcms.org)", "out": ("Backdrop CMS", "1")},
        {"in": "DSpace 6.2", "out": ("DSpace", "6.2")},
        {
            "in": "Discourse 2.5.0.beta5 - https://github.com/discourse/discourse version 2c880b9bf92a1efede9b8516ab9019358a01e879",
            "out": ("Discourse", "2.5.0.beta5")
        },
        {"in": "Drupal 7 (http://drupal.org)", "out": ("Drupal", "7")},
        {"in": "Koha 18.1106000", "out": ("Koha", "18.1106000")},
        {"in": "Microsoft FrontPage 4.0", "out": ("Microsoft FrontPage", "4.0")},
        {"in": "Microsoft Visual Studio .NET 7.1", "out": ("Microsoft Visual Studio .NET", "7.1")},
        {"in": "Microsoft Word 11", "out": ("Microsoft Word", "11")},
        {"in": "Mozilla/4.05 [en] (X11; I; Linux 2.1.88 i586) [Netscape]", "out": ("Mozilla", "4.05")},
        {"in": "Mozilla/4.75 [en] (Windows NT 5.0; U) [Netscape]", "out": ("Mozilla", "4.75")},
        {"in": "VIM - Vi IMproved 8.0", "out": ("VIM - Vi IMproved", "8.0")},
        {"in": "WPML ver:4.6.5 stt:9,1;", "out": ("WPML", "4.6.5")},
        {"in": "quarto-1.3.427", "out": ("quarto", "1.3.427")},
        {"in": "mkdocs-1.1.2, mkdocs-material-6.1.6", "out": ("mkdocs", "1.1.2")},
    ]

    assert VersionInfoManager.extract_version('dummy') is None

    for item in test_data:
        assert VersionInfoManager.extract_version(item["in"]) == ExtractedVersion(*item["out"])


def test_versioninfomanager_notequeryiterator(app, host, service_factory, note_factory):  # pylint: disable=unused-argument
    """test VersionInfoManager note query iterator"""

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=1),
        xtype='nmap.banner_dict',
        data='{"dummy": "1"}'
    )

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=2),
        xtype='nmap.banner_dict',
        data='invalid_dummy'
    )

    assert len(list(VersionInfoManager._jsondata_iterator(VersionInfoManager._base_note_query()))) == 1  # pylint: disable=protected-access


def test_versioninfomanager_collect_nmap_bannerdict(app, versioninfo_notes):  # pylint: disable=unused-argument
    """test VersionInfoManager.collect_nmap_bannerdict"""

    raw_map = VersionInfoManager.collect_nmap_bannerdict(RawMap())
    assert raw_map.len() == 6


def test_versioninfomanager_collect_nmap_httpgenerator(app, host, service_factory, note_factory):  # pylint: disable=unused-argument
    """test VersionInfoManager.collect_nmap_httpgenerator"""

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=81),
        xtype='nmap.http-generator',
        data='{"id": "http-generator", "output": "xproduct 1.2.3", "elements": {}}'
    )
    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=82),
        xtype='nmap.http-generator',
        data='{"id": "http-generator", "output": "yproduct", "elements": {}}'
    )

    raw_map = VersionInfoManager.collect_nmap_httpgenerator(RawMap())
    assert raw_map.len() == 1


def test_versioninfomanager_collect_nmap_mysqlinfo(app, host, service_factory, note_factory):  # pylint: disable=unused-argument
    """test VersionInfoManager.collect_nmap_mysqlinfo"""

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=3306),
        xtype='nmap.mysql-info',
        data='{"id": "mysql-info", "elements": {"Version": "5.5.5-10.3.38-MariaDB-1:10.3.38+maria~ubu2004-log"}}'
    )

    raw_map = VersionInfoManager.collect_nmap_mysqlinfo(RawMap())
    assert raw_map.len() == 1


def test_versioninfomanager_collect_nmap_rdpntlminfo(app, host, service_factory, note_factory):  # pylint: disable=unused-argument
    """test VersionInfoManager.collect_nmap_rdpntlminfo"""

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=3389),
        xtype='nmap.rdp-ntlm-info',
        data='{"id": "rdp-ntlm-info", "elements": {"Product_Version": "10.0.14393"}}'
    )

    raw_map = VersionInfoManager.collect_nmap_rdpntlminfo(RawMap())
    assert raw_map.len() == 1


def test_versioninfomanager_collect_cpes(app, host, service_factory, note_factory):  # pylint: disable=unused-argument
    """test VersionInfoManager.collect_cpes"""

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=22),
        xtype='cpe',
        data='["cpe:/a:openbsd:openssh:8.4p1", "cpe:/o:linux:linux_kernel", "invalid"]'
    )

    raw_map = VersionInfoManager.collect_cpes(RawMap())
    assert raw_map.len() == 1
