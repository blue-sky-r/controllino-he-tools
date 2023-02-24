#!/usr/bin/python3
#
# controllinohotspot console log classifier for analytics
#
# usage:
# > ws_tail.py -f console -p 123 controllinohotspot | ws_slassify.py | grcat conf.controllinohotspot
# get stats:
# > kill -USR1 $(pidof -x ws_classify.py) && sleep 1 && cat /tmp/stats

import sys
import json
import argparse
import re
import signal
import time

__VERSION__ = '2023.02.24'


# debog cmponents (csv)
#
DBGMODE = ''

# miner specific config
#
CONFIG = {
    # config for firmware version
    'miner_version': '2023.02.07.0',
    # match console log line parts
    # 2022-08-28 10:42:39.904 7 [error] <0.3591.0>@Undefined:Undefined:Undefined gen_server <0.3591.0> terminated with reason: connection_down
    # 2022-08-20 10:26:34.913 7 [info] <0.1746.0>@miner_lora_light:handle_udp_packet:{350,5} PULL_DATA from 12273815315514654720 on 57675
    'log': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d+ '
                       '\[(?P<level>\w+)\] '
                       '<[\d.]+>@(?P<facility>\w+:\w+(:[\w ]+)?):?[<{](?P<loc>[\d,.]+)[}>] '
                       '(?P<msg>.+)$'),
    # signal -> action name
    'signals': {
        signal.SIGUSR1: 'onsignal_usr1'     # create statfile
    },
    # whete the stats are written for further processing
    'statfile': '/tmp/stats',
    # classify sections
    'classify': {
        'level': {
            'desc': 'level count',
            'facility': None,
            'match': None,
            'onmatch': 'level_count_onmatch',
        },
        'facility': {
            'desc': 'facility count',
            'facility': None,
            'match': None,
            'onmatch': 'facility_count_onmatch',
        },
        'witness': {
            'desc': 'witnessing count and table',
            # 2023-02-22 22:43:51.481 8 [info] <0.1639.0>@miner_gateway_port:dispatch_port_logs:{195,13} [ gateway-rs ] received possible PoC payload: Packet(Packet { oui: 0, r#type: Lorawan, payload: [224, ... 253],
            # timestamp: 3892943259, signal_strength: -131.0, frequency: 868.5, datarate: "SF12BW125", snr: -18.5, routing: None, rx2_window: None }), module: beacon
            'facility': 'miner_gateway_port:dispatch_port_logs',
            'match': re.compile(r'\[ gateway-rs \] received possible PoC payload: Packet.+'
                                'signal_strength: (?P<rssi>-?\d+\.\d+), frequency: (?P<freq>\d+\.\d+), '
                                'datarate: "SF12BW125", snr: (?P<snr>-?\d+\.?\d*), routing: .+ module: beacon'),
            'onmatch': 'witnessing_onmatch',
            'table': {
                'header': 'Date Time GMT, Freq, RSSI, SNR',
                # float columns f will have average values calculated in the tab footer
                'format': '| {0:>23s} | {1:>6.2f} | {2:>6.1f} | {3:>5.1f} |',
                'footer': {
                    'max': 'witness MAXimal value',
                    'avg': 'witness AVeraGe value',
                    'min': 'witness MINimal value',
                    'empty': 'x',
                    'display': 'max, avg, min'
                },
                'maxrows': 10
            }
        },
        'uplink': {
            'desc': 'uplink received and table',
            # 2022-08-17 11:07:26.227 7 [info] <0.1647.0>@miner_mux_port:dispatch_port_logs:{118,13} [ gwmp-mux ] From AA:55:5A:00:00:00:00:00 received uplink: @3383561764 us, 868.10 MHz, DataRate(SF12, BW125), rssis: -142, snr: -22.2, len: 22
            'facility': 'miner_mux_port:dispatch_port_logs',
            'match': re.compile(
                r'\[ gwmp-mux \] From AA:55:5A:00:00:00:00:00 received uplink: @\d+ us, (?P<freq>\d+\.\d+) MHz, DataRate\((?P<sf>SF\d+), (?P<bw>BW\d+)\), rssis: (?P<rssi>-\d+), snr: (?P<snr>-?\d+\.?\d*), len: (?P<len>\d+)'
            ),
            'onmatch': 'uplink_onmatch',
            'table': {
                'header': 'Date Time GMT, Freq, SF, BW, RSSI, SNR, Len',
                # float columns f will have average values calculated in the tab footer
                'format': '| {0:>23s} | {1:>6.2f} | {2:<4s} {3:>5s} | {4:>6.1f} | {5:>5.1f} | {6:>5.1f} |',
                'footer': {
                    'max': 'uplink MAXimal value',
                    'avg': 'uplink AVeraGe value',
                    'min': 'uplink MINimal value',
                    'empty': 'x',
                    'display': 'max, avg, min'
                },
                'maxrows': 30
            }
        }
    }
}


def dbg(component, msg):
    """ print dbg msg if requested in global DBGMODE """
    if component not in DBGMODE: return
    print('= DBG =', component, '=', msg)


class Table:
    """ ASCII formatted text table helper """

    def __init__(self, headerstr, formatstr, footerstr, maxrows=None):
        """ init empty table as list  """
        self.tab = []
        self.headerstr = headerstr
        self.formatstr = formatstr
        self.footerstr = footerstr
        self.maxrows = maxrows

    def add_row(self, rowastuple):
        """ add row as tuple, remove the first item if maxrows has been reached """
        self.tab.append(rowastuple)
        if self.maxrows is not None and len(self.tab) > self.maxrows:
            self.tab.pop(0)

    def print(self, file=sys.stdout):
        """ formatted output with default formatting """
        self.printf(self.headerstr, self.formatstr, self.footerstr, file)

    def printf(self, headerstr, formatstr, footerstr, file=sys.stdout):
        """ parametric formatted output, headerstr = 'name1, name2' formatstr = '| {0:>23s} | {1:<5s} | {2:^9s} |', footerstr='text, text' """
        # column names to tuple
        colnames = tuple([ name.strip() for name in headerstr.split(',') ])
        # replace format float to string 6.1f -> 6s
        formatstrs = re.sub(r'(\d+)(\.\d+)?f\}', r'\1s}', formatstr)
        # create row separator from formatstr (use empty string as data)
        rowsep = formatstrs.format(*tuple([' ' for i in colnames])).replace(' ', '-').replace('|', '+')
        # header - print column names centered
        print(rowsep, file=file)
        # mod left and right align to centered
        print(formatstrs.replace('>', '^').replace('<', '^').format(*colnames), file=file)
        print(rowsep, file=file)
        # min,max,avg values for footer
        stat = {}
        # data rows
        for rowidx,row in enumerate(self.tab):
            print(formatstr.format(*row), file=file)
            # calc avg only for float values
            # init on the first pass
            if not stat:
                stat['min'] = [ value if type(value) == float else footerstr['empty'] for value in row ]
                stat['max'] = [ value if type(value) == float else footerstr['empty'] for value in row ]
                stat['avg'] = [ 0 if type(value) == float else footerstr['empty'] for value in row ]
            # hold min. max and calc avg values
            for idx,value in enumerate(row):
                if type(value) == float:
                    stat['min'][idx] = value if value < stat['min'][idx] else stat['min'][idx]
                    stat['max'][idx] = value if value > stat['max'][idx] else stat['max'][idx]
                    stat['avg'][idx] = (rowidx * stat['avg'][idx] + value) / (rowidx + 1)
        # write stats to the file
        print(rowsep, file=file)
        # footer only if we have avg
        if stat:
            for typ in footerstr.get('display').split(', '):
                stat[typ][0] = footerstr[typ]
                print(formatstr.format(*stat[typ]), file=file)
            print(rowsep, file=file)


class Classifier:
    """ configurable console log fclassifier """

    def __init__(self, cfg):
        """ init cfg and global level/facility counters """
        # config
        self.cfg = cfg
        # counters
        self.cnt = {}
        # tables
        self.tab = {}
        # process config to add counters and tables
        for section, entry in cfg.get('classify').items():
            # add counter
            self.cnt[section] = {}
            # add table if defined
            table = entry.get('table')
            if table:
                self.tab[section] = Table(table['header'], table['format'], table['footer'], table.get('maxrows'))
        # attach signal handlers
        for sig, fncname in CONFIG.get('signals').items():
            signal.signal(sig, self.__getattribute__(fncname))

    def stat_count(self, cntname, match, key=None):
        """ cnt[cntname][match[key]]++ """
        if key is None:
            key = match[cntname] if match else 'n/a'
        cnt = self.cnt[cntname]
        cnt[key] = 1 + cnt.get(key, 0)

    def level_count_onmatch(self, line, linematch, msgmatch):
        """ count levels """
        self.stat_count('level', linematch)

    def facility_count_onmatch(self, line, linematch, msgmatch):
        """ count facilities """
        self.stat_count('facility', linematch)

    def witnessing_onmatch(self, line, linematch, msgmatch):
        """ he witness """
        self.stat_count('witness', linematch, 'sending witness')
        self.tab['witness'].add_row((
            linematch['datetime'],
            float(msgmatch['freq']),
            float(msgmatch['rssi']),
            float(msgmatch['snr'])
        ))

    def uplink_onmatch(self, line, linematch, msgmatch):
        """ lora uplink """
        self.stat_count('uplink', linematch, 'received uplink')
        self.tab['uplink'].add_row((
            linematch['datetime'],
            float(msgmatch['freq']),
            msgmatch['sf'],
            msgmatch['bw'],
            float(msgmatch['rssi']),
            # add decimal .0 for integer values for alignment
            float(msgmatch['snr']),
            float(msgmatch['len'])
        ))

    def classify(self, line):
        """ classify the log line """
        regex = self.cfg.get('log')
        # without regex just passtrough - no classification
        if regex is None: return
        #
        linematch = regex.match(line)
        #
        for section, entry in self.cfg.get('classify').items():
            # check facility string match if configured
            if entry.get('facility'):
                if not linematch or entry['facility'] != linematch['facility']:
                    continue
            # msg regex match if configured
            msgmatch = None
            if entry.get('match') and linematch:
                msgmatch = entry['match'].match(linematch['msg'])
                if msgmatch is None:
                    continue
            # call onmatch fnc if defined
            if entry.get('onmatch'):
                self.__getattribute__(entry.get('onmatch'))(line, linematch, msgmatch)

    def output_stats(self, file=sys.stdout):
        """ counters and tabs to file """
        # counters
        for section, entry in self.cfg.get('classify').items():
            print('section#:', section, end=' ', file=file)
            #print(self.cnt[section], file=file); print()
            print(json.dumps(self.cnt[section], indent=4, sort_keys=True), file=file)
            print(file=file)
            # optional tables
            if self.tab.get(section):
                self.tab[section].print(file)
                print(file=file)

    def onsignal_usr1(self, signum, frame):
        """ write stats on signal, e.g. > kill -signal pid """
        fname = self.cfg.get('statfile')
        if not fname:
            print('ERR - stats file not configured')
            return
        with open(fname, mode='w') as file:
            self.output_stats(file=file)


if __name__ == "__main__":
    # cli pars - https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(description='classify controllino miner console log reading from stdin',
                                     epilog='example: ws_tail.py -f con controllino | ws_classify.py')
    parser.add_argument('-q', '--quiet', default=False, required=False, action="store_true",
                        help='quiet mode, do not passthrough processed line (default pass all lines to stdout)')
    parser.add_argument('-s', '--stats', default=False, required=False, action="store_true",
                        help='print final statistics on input eof (default no)')
    parser.add_argument('-d', '--debug', metavar='c1[,c2]', default='', required=False,
                        help='enable debug for component (par for pars, cl for classifier)')
    args = parser.parse_args()
    DBGMODE = args.debug

    #
    c = Classifier(CONFIG)
    # process stdin
    for line in sys.stdin:
        # optional passthrough
        if not args.quiet:
            print(line, end='')
        # classify
        c.classify(line)
    # optional final stats
    if args.stats:
        c.output_stats()
