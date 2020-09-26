# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent execution modules
"""

import json
import logging
import os
import re
import shlex
import signal
import subprocess
from abc import ABC, abstractmethod
from ipaddress import AddressValueError, IPv6Address
from pathlib import Path
from socket import AF_INET6, getaddrinfo, gethostbyaddr
from time import sleep

from schema import Schema, Optional


registered_modules = {}  # pylint: disable=invalid-name


def register_module(name):
    """register module class to registry"""

    def register_module_real(cls):
        if cls not in registered_modules:
            registered_modules[name] = cls
        return cls
    return register_module_real


class ModuleBase(ABC):
    """
    Base class for agent modules.

    For ABNF target specifications literals not explicitly specified here see
    'RFC 3986 Appendix A: Collected ABNF for URI' (https://tools.ietf.org/html/rfc3986#appendix-A)
    """

    CONFIG_SCHEMA = Schema({
        'module': str
    })

    def __init__(self):
        self.log = logging.getLogger(f'sner.agent.module.{self.__class__.__name__}')
        self.process = None

    @abstractmethod
    def run(self, assignment):  # pylint: disable=no-self-use
        """run module for assignment"""

        Path('assignment.json').write_text(json.dumps(assignment))
        self.CONFIG_SCHEMA.validate(assignment['config'])

    @abstractmethod
    def terminate(self):
        """terminate method; should terminate module immediatelly"""

    def _terminate(self):  # pragma: no cover  ; running over multiprocessing
        """terminate executed command"""

        if self.process and (self.process.poll() is None):
            try:
                os.kill(self.process.pid, signal.SIGTERM)
            except OSError as e:
                self.log.error(e)

    def _execute(self, cmd, output_file='output'):
        """execute command and capture output"""

        cmdarg = shlex.split(cmd) if isinstance(cmd, str) else cmd
        with open(output_file, 'w') as output_fd:
            self.process = subprocess.Popen(cmdarg, stdin=subprocess.DEVNULL, stdout=output_fd, stderr=subprocess.STDOUT)
            retval = self.process.wait()
            self.process = None
        return retval


@register_module('dummy')
class Dummy(ModuleBase):
    """
    testing module implementation

    ## target specification

    target = 1*CHAR
    """

    CONFIG_SCHEMA = Schema({
        'module': 'dummy',
        'args': str
    })

    def run(self, assignment):
        """simply write assignment and return"""

        super().run(assignment)
        return 0

    def terminate(self):
        """nothing to be done for dummy terminate"""


@register_module('nmap')
class Nmap(ModuleBase):
    """
    nmap module

    ## target specification

    target = IPv4address / reg-name / IPv6address / "[" IPv6address "]" / "[" reg-name "]"
    """

    CONFIG_SCHEMA = Schema({
        'module': 'nmap',
        'args': str,
        Optional('timing_perhost'): int
    })

    def __init__(self):
        super().__init__()
        self.doscan = True

    @staticmethod
    def sort_ipv6_targets(intargets):
        """split v4 and v6 targets"""

        targets, targets6 = [], []

        for target in intargets:
            # brackets enforces target to be ipv6 (mostly for hostnames)
            if (target[0] == '[') and (target[-1] == ']'):
                targets6.append(target[1:-1])
                continue

            # default ipv6 addr detection
            try:
                IPv6Address(target)
                targets6.append(target)
                continue
            except AddressValueError:
                pass

            # all other targets
            targets.append(target)

        return targets, targets6

    def run_scan(self, assignment, targets, targets_file, output_file, extra_args=None):  # pylint: disable=too-many-arguments
        """run scan"""

        Path(targets_file).write_text('\n'.join(targets))

        timing_args = []
        if 'timing_perhost' in assignment['config']:
            output_rate = assignment['config']['timing_perhost'] * len(targets)
            timing_args = [
                '--max-retries', '3',
                '--script-timeout', '10m',
                '--min-hostgroup', str(len(targets)),
                '--min-rate', str(output_rate),
                '--max-rate', str(int(output_rate * 1.05))
            ]

        output_args = ['-oA', output_file, '--reason']
        target_args = ['-iL', targets_file]

        cmd = ['nmap'] + (extra_args or []) + shlex.split(assignment['config']['args']) + timing_args + output_args + target_args
        return self._execute(cmd, output_file)

    def run(self, assignment):
        """run the agent"""

        ret = 0
        super().run(assignment)

        targets, targets6 = self.sort_ipv6_targets(assignment['targets'])
        if targets and self.doscan:
            ret |= self.run_scan(assignment, targets, 'targets', 'output')
        if targets6 and self.doscan:
            ret |= self.run_scan(assignment, targets6, 'targets6', 'output6', extra_args=['-6'])
        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.doscan = False
        self._terminate()


@register_module('manymap')
class Manymap(ModuleBase):
    """
    internet endpoints nmap-based scanner

    ## target specification

    proto    = "tcp" / "udp"
    hostspec = IPv4address / reg-name / "[" IPv6address "]" / "[" reg-name "]"
    port     = 1*DIGIT
    target   = proto "://" hostspec ":" port
    """

    CONFIG_SCHEMA = Schema({
        'module': 'manymap',
        'args': str,
        'delay': int,
    })

    TARGET_REGEXP = r'^(?P<proto>tcp|udp)://(?P<host>[0-9\.]{7,15}|[0-9a-zA-Z\.\-]{1,256}|\[[0-9a-fA-F:]{3,45}\]|\[[0-9a-zA-Z\.\-]{1,256}\]):(?P<port>[0-9]+)$'  # noqa: 501  pylint: disable=line-too-long

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        ret = 0
        super().run(assignment)

        for idx, target in enumerate(assignment['targets']):
            mtmp = re.match(self.TARGET_REGEXP, target)
            if mtmp:
                output_args = ['-oA', f'output-{idx}', '--reason']
                target_args = ['-p', f'{mtmp.group("proto")[0].upper()}:{mtmp.group("port")}']
                host = mtmp.group('host')
                if (host[0] == '[') and (host[-1] == ']'):
                    target_args += ['-6', host[1:-1]]
                else:
                    target_args += [host]

                cmd = ['nmap'] + shlex.split(assignment['config']['args']) + output_args + target_args
                ret |= self._execute(cmd, f'output-{idx}')
                sleep(assignment['config']['delay'])
            else:
                self.log.warning('invalid target: %s', target)

            if not self.loop:  # pragma: no cover  ; not tested
                break

        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()


@register_module('six_dns_discover')
class SixDnsDiscover(ModuleBase):
    """
    dns based ipv6 from ipv4 address discover
    """

    CONFIG_SCHEMA = Schema({
        'module': 'six_dns_discover',
        'delay': int
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)

        result = {}
        for addr in assignment['targets']:
            try:
                (hostname, _, _) = gethostbyaddr(addr)
                resolved_addrs = getaddrinfo(hostname, None, AF_INET6)
                for _, _, _, _, sockaddr in resolved_addrs:
                    result[sockaddr[0]] = (hostname, addr)
            except OSError:
                continue
            finally:
                sleep(assignment['config']['delay'])

            if not self.loop:  # pragma: no cover  ; not tested
                break

        Path('output.json').write_text(json.dumps(result))
        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False


@register_module('six_enum_discover')
class SixEnumDiscover(ModuleBase):
    """
    enumeration based ipv6 discover

    man scan6
    -d DST_ADDRESS, --dst-address DST_ADDRESS
    This  option  specifies the target address prefix/range of the address scan. An IPv6 prefix can be specified in the form 2001:db8::/64,
    or as 2001:db8:a-b:1-10 (where specific address ranges are specified for the two low order 16-bit words). This option must be specified
    for remote address scanning attacks.

    ## target specification

    target   = scan6-dst-address
    """

    CONFIG_SCHEMA = Schema({
        'module': 'six_enum_discover',
        'rate': int,
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        ret = 0
        super().run(assignment)

        for idx, target in enumerate(assignment['targets']):
            ret |= self._execute(['scan6', '--rate-limit', f'{assignment["config"]["rate"]}pps', '--dst-address', target], f'output-{idx}.txt')
            if not self.loop:  # pragma: no cover  ; not tested
                break

        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
