#!/usr/bin/env python3
"""low overhead network statistics"""

import argparse
import logging
import time
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(levelname)s %(message)s')
logger = logging.getLogger()  # pylint: disable=invalid-name
sys.tracebacklimit = None


def parse_arguments():
    """parse arguments"""

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--iface', default='eth0', help='interface name')
    parser.add_argument('--time', type=int, default=1, help='time period')
    parser.add_argument('--single', action='store_true', help='print one statistic and exit')
    parser.add_argument('--csv', action="store_true", help='print csv raw output')
    parser.add_argument('--noheader', action='store_true', help='do not print header')
    return parser.parse_args()


def sizeof_fmt(num, suffix='B'):
    """convert to human readable form"""

    for unit in [' ', 'k', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1000.0:
            return '%3.1f %1s%s' % (num, unit, suffix)
        num /= 1000.0
    return '%.1f %1s%s' % (num, 'Y', suffix)


def stats_tcp_read():
    """read tcp stats from proc"""

    # https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/tree/include/net/tcp_states.h
    tran = [
        'padding', 'TCP_ESTABLISHED', 'TCP_SYN_SENT', 'TCP_SYN_RECV', 'TCP_FIN_WAIT1', 'TCP_FIN_WAIT2',
        'TCP_TIME_WAIT', 'TCP_CLOSE', 'TCP_CLOSE_WAIT', 'TCP_LAST_ACK', 'TCP_LISTEN',
        'TCP_CLOSING', 'TCP_NEW_SYN_RECV', 'undefined1', 'undefined2', 'TCP_MAX_STATES'
    ]

    data = []
    with open('/proc/net/tcp', 'r') as ftmp:
        data += ftmp.readlines()[1:]
    with open('/proc/net/tcp6', 'r') as ftmp:
        data += ftmp.readlines()[1:]

    stat_by_state = dict(zip(tran, [0 for x in range(len(tran))]))
    for line in data:
        state = tran[int(line.split()[3], 16)]
        stat_by_state[state] += 1

    logger.debug(stat_by_state)
    return stat_by_state


def stats_rxtx_read(iface):
    """read rxtx stats from proc"""

    iface_prefix = '%s:' % iface
    rx_columns = ['bytes', 'packets', 'errs', 'drop', 'fifo', 'frame', 'compressed', 'multicast']
    tx_columns = ['bytes', 'packets', 'errs', 'drop', 'fifo', 'colls', 'carrier', 'compressed']

    line = None
    with open('/proc/net/dev', 'r') as ftmp:
        for tmpline in [x.strip() for x in ftmp.readlines()]:
            if tmpline.startswith(iface_prefix):
                line = tmpline
                break

    if line:
        # face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
        # eth0: 76594958  122515    7    0    0     0          0         0 72115331  110248    0    0    0     0       0          0
        logger.debug(line)
        ret = {
            "rx": dict(zip(rx_columns, map(int, line.split()[1:8]))),
            "tx": dict(zip(tx_columns, map(int, line.split()[9:16])))
        }
    else:
        raise RuntimeError('interface statistics not found')

    logger.debug(ret)
    return ret


def stats_diff(old, new, timespan):
    """count vals per seconds in two vectors"""

    keys = old.keys()
    vals = [int((new[x] - old[x])/timespan) for x in keys]
    return dict(zip(keys, vals))


def stats(iface, timespan):
    """grab stats from system"""

    # 1. grab stats over timespan
    stats_rxtx_old = stats_rxtx_read(iface)
    time.sleep(timespan)
    stats_rxtx_new = stats_rxtx_read(iface)
    stats_tcp = stats_tcp_read()

    # 2. postprocess
    # rxtx stats
    diff = {
        'rx': stats_diff(stats_rxtx_old['rx'], stats_rxtx_new['rx'], timespan),
        'tx': stats_diff(stats_rxtx_old['tx'], stats_rxtx_new['tx'], timespan)
    }
    logger.debug(diff)

    # tcp stats group by statemachine states
    # active - action initiated by localhost, passive - action initiated by remote peer
    tcp_open_active = stats_tcp['TCP_SYN_SENT']
    tcp_open_passive = sum([stats_tcp[x] for x in ['TCP_SYN_RECV', 'TCP_NEW_SYN_RECV']])
    tcp_close_active = sum([stats_tcp[x] for x in ['TCP_FIN_WAIT1', 'TCP_FIN_WAIT2', 'TCP_CLOSING', 'TCP_TIME_WAIT']])
    tcp_close_passive = sum([stats_tcp[x] for x in ['TCP_CLOSE_WAIT', 'TCP_LAST_ACK']])

    # 3. generate output
    # iface rx/tx bits, bytes, packets
    # globalwide 4+6 tcp: opening active / passive | listen / established | closing active / passive
    return [
        8*diff['rx']['bytes'], diff['rx']['bytes'], diff['rx']['packets'],
        8*diff['tx']['bytes'], diff['tx']['bytes'], diff['tx']['packets'],
        tcp_open_active, tcp_open_passive,
        stats_tcp['TCP_LISTEN'], stats_tcp['TCP_ESTABLISHED'],
        tcp_close_active, tcp_close_passive
    ]


def main():
    """main"""

    # arguments
    args = parse_arguments()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        sys.tracebacklimit = 0

    # output format
    if args.csv:
        columns = [
            'rx_bits', 'rx_bytes', 'rx_packets',
            'tx_bits', 'tx_bytes', 'tx_packets',
            'tcp_open_active', 'tcp_open_passive',
            'tcp_listen', 'tcp_established',
            'tcp_close_active', 'tcp_close_passive'
        ]
        outfmt = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s'
        if not args.noheader:
            print(outfmt % tuple(columns))
    else:
        columns = [
            'bits', 'bytes', 'packets',
            'bits', 'bytes', 'packets',
            'open_active', 'open_passive',
            'listen', 'esablished',
            'close_active', 'close_passive']
        outfmt = 'rx: %10s %10s %10s    tx: %10s %10s %10s    tcp: %4s/%4s | %4s/%4s | %4s/%4s'
        if not args.noheader:
            print(outfmt % tuple(columns))

    # main task
    try:
        while True:
            data = stats(args.iface, args.time)
            if not args.csv:
                data[0] = sizeof_fmt(data[0], 'b')
                data[1] = sizeof_fmt(data[1], 'B')
                data[2] = sizeof_fmt(data[2], 'p')
                data[3] = sizeof_fmt(data[3], 'b')
                data[4] = sizeof_fmt(data[4], 'B')
                data[5] = sizeof_fmt(data[5], 'p')
            print(outfmt % tuple(data))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    sys.exit(main())
