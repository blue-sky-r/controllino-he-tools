#!/usr/bin/python3
#
# utility to tail remote log files via websocket ws:// connection
#
# requires: sudo pip3 install websocket-client # https://github.com/websocket-client/websocket-client
#

# ws_classify -l name.log ... create log from stdin (default
# ws_classify -s type ... statistics classifier, type is [ count, calls, lora, push/pull data.  ]
#

import sys
import json
import argparse
import re
import signal
import time

__VERSION__ = '2022.08.20'



# debog cmponents (csv)
#
DBGMODE = ''

def dbg(component, msg):
    """ print dbg msg if requested in global DBGMODE """
    if component not in DBGMODE: return
    print('= DBG =', component, '=', msg)


class Classifier:

    def __init__(self, cfg):
        """ init cfg and global level/facility counters """
        self.cfg = cfg
        # counters
        self.cnt = {
            'level': { },
            'facility': { }
        }
        # tables
        self.tab = {
            'witness': []
        }

    def stat_count(self, cntname, match, key=None):
        """ cnt[cntname][match[key]]++ """
        if key is None:
            key = match[cntname] if match else 'n/a'
        cnt = self.cnt[cntname]
        cnt[key] = 1 + cnt.get(key, 0)

    def level_count_onmatch(self, line, linematch, msgmatch):
        """ count levels """
        #print('level_count_onmatch()', line)
        self.stat_count('level', linematch)

    def level_count_onsignal(self):
        """ """
        print(self.cnt['level'])

    def facility_count_onmatch(self, line, linematch, msgmatch):
        """ count facilities """
        #print('facility_count_onmatch()', line)
        self.stat_count('facility', linematch)

    def facility_count_onsignal(self):
        """ """
        print(self.cnt['facility'])

    def witnessing_onmatch(self, line, linematch, msgmatch):
        """ """
        #print('witnessing_onmatch()', line)
        self.tab['witness'].append({
            linematch['datetime']: {
                'freq': msgmatch['freq'],
                'rssi': msgmatch['rssi'],
                'snr': msgmatch['snr']
            }
        })

    def classify(self, line):
        """ classify the log line """
        regex = self.cfg.get('log')
        # without regex just passtrough - no classification
        if regex is None: return
        #
        linematch = regex.match(line)
        # level
        #self.stat_count('level', linematch)
        # facility
        #self.stat_count('facility', linematch)
        #
        for sig, sigcfg in self.cfg.get('classify').items():
            # check facility string match if configured
            if sigcfg.get('facility'):
                if not linematch or sigcfg['facility'] != linematch['facility']:
                    continue
            # msg regex match if configured
            msgmatch = None
            if sigcfg.get('match') and linematch:
                msgmatch = sigcfg['match'].match(linematch['msg'])
                if msgmatch is None: continue
            #
            if sigcfg.get('onmatch'):
                sigcfg['onmatch'](self, line, linematch, msgmatch)

    def print_table(self, table):
        """ * date time * f * rate * rssi * snr * """
        # https://realpython.com/python-formatted-output/
        rowsep = '+-------------------------+-------+-----------+------+-------+'
        colname = ('date time', 'fre', 'datarate', 'rssi', 'snr')
        frmstr = '| {:>23s} | {:>5s} | {:>9s} | {:>4s} | {:>5s} |'
        #
        print(rowsep)
        print(frmstr.replace('>','^').format(*colname))
        print(rowsep)
        for row in table:
            print(frmstr.format(*row))
        print(rowsep)


# miner specific config
#
CONFIG = {
    # config for firmware version
    'miner_version': '2022.08.17.1',
    # match log line parts
    # 2022-08-20 10:26:34.913 7 [info] <0.1746.0>@miner_lora_light:handle_udp_packet:{350,5} PULL_DATA from 12273815315514654720 on 57675
    'log': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d+ '
                       '\[(?P<level>\w+)\] '
                       '(<[\d.]+>@(?P<facility>\w+:\w+):\{(?P<loc>\d+,\d+)\} )?'
                       '(?P<msg>.+)$'),
    # signal actions
    'classify': {
        signal.SIGUSR1: {
            'desc': 'level',
            'facility': None,
            'match': None,
            'onmatch': Classifier.level_count_onmatch,
            'onsignal': Classifier.level_count_onsignal,
        },
        signal.SIGUSR2: {
            'desc': 'facility',
            'facility': None,
            'match': None,
            'onmatch': Classifier.facility_count_onmatch,
            'onsignal': Classifier.facility_count_onsignal,
        },
        signal.SIGRTMIN: {
            'desc': 'witnessing',
            # 2022-07-20 16:07:19.027 8 [info] <0.1778.0>@miner_onion_server_light:decrypt:{230,13} sending witness at RSSI: -139, Frequency: 867.1, SNR: -19.5
            'facility': 'miner_onion_server_light:decrypt',
            'match': re.compile(r'sending witness at RSSI: (?P<rssi>-\d+), Frequency: (?P<freq>\d+\.\d+), SNR: (?P<snr>(-?\d+\.?\d*))'),
            'onmatch': Classifier.witnessing_onmatch,
            'onsignal': None,
        }
    }
}

class WSClient:

    def on_usr1(self, signum, frame):
        """ kill -USR1 $pid """
        print("=== statistics === signum:", signum, "=", self.classifier.cnt, "=")
        self.stat_file('/tmp/usr1', self.classifier.cnt)

    def on_usr2(self, signum, frame):
        """ kill -USR2 $pid """
        print("=== statistics === signum:", signum, "=", self.classifier.call, "=")
        self.stat_file('/tmp/usr2', self.classifier.call)

    def stat_file(self, fname='/tmp/file', data={}):
        """ create stat file """
        with open(fname, 'w') as f:
            f.write(json.dumps(data))


if __name__ == "__main__":
    # cli pars
    parser = argparse.ArgumentParser(description='classify controllino miner log reading from stdin',
                                     epilog='example: ws_tail.py -f con controllino | ws_classify -l console.log')
    #parser.add_argument('wserver',  metavar='[ws[s]://]host', help='websocket server to connect to')
    parser.add_argument('-l', '--log',   metavar='logfile', default='', required=False,
                        help='copy stdin to logfile (default to stdout)')
    parser.add_argument('-c', '--classify', default='', required=False,
                        help='use internal classifier')
    parser.add_argument('-d', '--debug', metavar='c1[,c2]', default='', required=False,
                        help='enable debug for component (par for pars, cl for classifier)')
    args = parser.parse_args()
    DBGMODE = args.debug

    # signals
    #signal.signal(signal.SIGUSR1, wsc.on_usr1)
    #signal.signal(signal.SIGUSR2, wsc.on_usr2)
    c = Classifier(CONFIG)
    #with open('console.log', 'r') as f:
    #    for line in f:
    #        c.classify(line)
    #        break
    for line in sys.stdin:
        print(line, end='')
        c.classify(line)
    #
    print('=')
    print('LEVEL:'); print(c.cnt['level'])
    print('=')
    print('FACILITY:'); print(c.cnt['facility'])
    print('=')
    print('WITNESS:'); print(c.tab['witness'])

