# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage test models
"""

from factory import SubFactory

from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln
from tests import BaseModelFactory


class HostFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test host model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test host model factory"""
        model = Host

    address = '127.128.129.130'
    hostname = 'localhost.localdomain'
    os = 'some linux'
    comment = 'testing webserver'


class ServiceFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test service model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test service model factory"""
        model = Service

    host = SubFactory(HostFactory)
    proto = 'tcp'
    port = 22
    state = 'up:syn-ack'
    name = 'ssh'
    info = 'product: OpenSSH version: 7.4p1 Debian 10+deb9u4 extrainfo: protocol 2.0 ostype: Linux'
    comment = 'a test service comment'


class VulnFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test vuln model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test vuln model factory"""
        model = Vuln

    host = SubFactory(HostFactory)
    service = None
    name = 'some vulnerability'
    xtype = 'scannerx.moduley'
    severity = SeverityEnum.unknown
    descr = 'a vulnerability description'
    data = 'vuln proof'
    refs = ['URL-http://localhost/ref1', 'ref2']
    tags = ['tag1', 'tag2']
    comment = 'some test vuln comment'


class NoteFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test note model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test note model factory"""
        model = Note

    host = SubFactory(HostFactory)
    service = None
    xtype = 'testnote.xtype'
    data = 'test note data'
    comment = 'some test note comment'
