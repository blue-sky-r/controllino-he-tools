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

__VERSION__ = '2022.05.16'

# miner config
#
MINER = {
    'console.log': {
        # 2022-04-28 20:24:07.116 7 [notice] <0.12157.58>@libp2p_yamux_session:handle_info:{189,5} Session liveness failure
        'line': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d '
                           '\[(?P<level>\w+)\] '
                           '<[\d.]+>@(?P<call>\w+:\w+):\{(?P<loc>\d+,\d+)\} '
                           '(?P<msg>.+)$'),
        # 2022-05-14 12:51:55.094 7 [info] <0.1812.0>@blockchain_state_channels_client:handle_packet:{381,5} handle_packet
        #  #packet_pb{oui=0,type=lorawan,payload=<<64,216,... 233,11>>,
        #  timestamp=2442868054,signal_strength=-116,frequency=867.1,datarate=<<"SF9BW125">>,snr=1.8,
        #  routing=#routing_information_pb{data={devaddr,2386136536}},rx2_window=undefined} to
        #  ["/p2p/11w77YQLhgUt8HUJrMtntGGr97RyXmot1ofs5Ct2ELTmbFoYsQa","/p2p/11afuQSrmk52mgxLu91AdtDXbJ9wmqWBUxC3hvjejoXkxEZfPvY"] with handler blockchain_state_channel_handler
        # 2022-05-14 12:53:28.300 7 [info] <0.1812.0>@blockchain_state_channels_client:handle_packet:{381,5} handle_packet #packet_pb{oui=0,type=lorawan,payload=<<64,32,8,192,1,128,182,58,8,171,26,135,191,246,78,243,1,32,219,40,100,46>>,timestamp=2536076792,signal_strength=-138,frequency=868.1,datarate=<<"SF12BW125">>,snr=-20.8,routing=#routing_information_pb{data={devaddr,29362208}},rx2_window=undefined} to ["/p2p/11w77YQLhgUt8HUJrMtntGGr97RyXmot1ofs5Ct2ELTmbFoYsQa","/p2p/11afuQSrmk52mgxLu91AdtDXbJ9wmqWBUxC3hvjejoXkxEZfPvY"] with handler blockchain_state_channel_handler
        'call': {
            'blockchain_state_channels_client:handle_packet': re.compile(r'timestamp=(?P<timestamp>\d+),'
                                                                        'signal_strength=(?P<rssi>-\d+),'
                                                                        'frequency=(?P<frequency>\d+\.\d),'
                                                                        'datarate=<<"(?P<datarate>\w+)">>,'
                                                                        'snr=(?P<snr>-?\d+.\d),'
                                                                         ),
        }
    },
    'error.log': {
        # 2022-05-12 13:49:40.460 [error] <0.32357.0>@libp2p_stream_relay:handle_server_data:{193,13} fail to pass request
        # 2022-05-15 17:34:41.239 [error] <0.30914.7> CRASH REPORT Process <0.30914.7> with 0 neighbours exited with reason: etimedout in gen_server:init_it/6 line 407
        'line': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) '
                           '\[(?P<level>\w+)\] '
                           '(<[\d.]+>@(?P<call>\w+:\w+):\{(?P<loc>\d+,\d+)\} )?'
                           '(?P<msg>.+)$'),
    },
}

# lorawan
# 2022-05-15 23:57:00.272 7 [info] <0.1812.0>@blockchain_state_channels_client:handle_packet:{381,5} handle_packet #packet_pb{oui=0,type=lorawan,payload=<<64,152,23,192,1,128,119,14,8,200,255,188,37,18,65,52,109,117,110,189,215,82>>,timestamp=4194026233,signal_strength=-135,frequency=868.3,datarate=<<"SF12BW125">>,snr=-19.0,routing=#routing_information_pb{data={devaddr,29366168}},rx2_window=undefined} to ["/p2p/11w77YQLhgUt8HUJrMtntGGr97RyXmot1ofs5Ct2ELTmbFoYsQa","/p2p/11afuQSrmk52mgxLu91AdtDXbJ9wmqWBUxC3hvjejoXkxEZfPvY"] with handler blockchain_state_channel_handler
#
CONFIG = {
    'line': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d+? '
                       '\[(?P<level>\w+)\] '
                       '(<[\d.]+>@(?P<facility>\w+:\w+):\{(?P<loc>\d+,\d+)\} )?'
                       '(?P<msg>.+)$'),
    'data': {
        # 2022-05-17 20:26:17.842 7 [info] <0.1840.0>@miner_lora_light:handle_udp_packet:{350,5} PULL_DATA from 12273815315514654720 on 55215
        # 2022-05-17 20:26:18.860 7 [info] <0.1840.0>@miner_lora_light:handle_udp_packet:{326,5} PUSH_DATA [{<<"stat">>,[{<<"time">>,<<"2022-05-17 20:26:18 GMT">>},{<<"rxnb">>,0},{<<"rxok">>,0},{<<"rxfw">>,0},{<<"ackr">>,100.0},{<<"dwnb">>,0},{<<"txnb">>,0},{<<"temp">>,30.0}]}] from 12273815315514654720 on 47826
        'miner_lora_light:handle_udp_packet': re.compile(r'(?P<pushpull>PUSH_DATA|PULL_DATA) '),
    },
    'rf': {
        # 2022-05-17 20:24:23.494 7 [info] <0.1812.0>@blockchain_state_channels_client:handle_packet:{381,5} handle_packet #packet_pb{oui=0,type=lorawan,payload=<<64,114,103,95,31,128,237,1,8,8,118,102,150,209,73,226,231,163,5,185,131,221>>,timestamp=1028534895,signal_strength=-132,frequency=867.3,datarate=<<"SF12BW125">>,snr=-14.2,routing=#routing_information_pb{data={devaddr,526346098}},rx2_window=undefined} to ["/p2p/11w77YQLhgUt8HUJrMtntGGr97RyXmot1ofs5Ct2ELTmbFoYsQa","/p2p/11afuQSrmk52mgxLu91AdtDXbJ9wmqWBUxC3hvjejoXkxEZfPvY"] with handler blockchain_state_channel_handler
        'blockchain_state_channels_client:handle_packet': re.compile(r'timestamp=(?P<timestamp>\d+),'
                                                                    'signal_strength=(?P<rssi>-\d+),'
                                                                    'frequency=(?P<frequency>\d+\.\d),'
                                                                    'datarate=<<"(?P<datarate>\w+)">>,'
                                                                    'snr=(?P<snr>-?\d+.\d),'
                                                                     ),
    },
    'lora': {
        # 2022-05-17 20:22:41.912 7 [info] <0.1840.0>@miner_lora_light:handle_udp_packet:{326,5} PUSH_DATA [{<<"rxpk">>,[[{<<"jver">>,1},{<<"tmst">>,926958312},{<<"chan">>,6},{<<"rfch">>,0},{<<"freq">>,867.7},{<<"mid">>,0},{<<"stat">>,1},{<<"modu">>,<<"LORA">>},{<<"datr">>,<<"SF12BW125">>},{<<"codr">>,<<"4/5">>},{<<"rssis">>,-136},{<<"lsnr">>,-19.0},{<<"foff">>,7417},{<<"rssi">>,-117},{<<"size">>,63},{<<"data">>,<<"QLx7WwCDigUG7hxk4GxouN52MlHt/+9RqlQinStng+WNClFWpPK6NJOzOcA/xXzAA1ydnoc7qayHYJbRyHUT">>}]]}] from 12273815315514654720 on 47826
        'miner_lora_light:handle_udp_packet': re.compile(r'')
    }
}

# debog cmponents (csv)
#
DBGMODE = ''

def dbg(component, msg):
    """ print dbg msg if requested in global DBGMODE """
    if component not in DBGMODE: return
    print('= DBG =', component, '=', msg)


class Classifier:

    def __init__(self, cfg):
        """ """
        self.cfg = cfg
        self.cnt = {
            'level': {
                'n/a': 0
            },
            'facility': {
                'n/a': 0
            },
            'data': {
            },
            'gateway': {
                'sent': 0,
                'received': 0,
                'dropped': 0
            }
        }
        self.detail = {
            'rf': [],
            'gateway': []
        }

    def stat_count(self, section, key):
        """ cnt[section][key]++ """
        cnt = self.cnt[section]
        cnt[key] = 1 + cnt.get(key, 0)

    def stat_detail_add(self, key, data):
        """ add data to detail[key] """
        self.detail[key].append(data)

    def stat_detail_rf(self, match):
        """ rf """
        regex = self.cfg.get('rf')
        if regex is None: return
        facility = match['facility']
        regex = regex.get(facility)
        if regex is None: return
        m = regex.search(match['msg'])
        if not m: return
        self.stat_detail_add('rf', (match['datetime'], m['frequency'], m['datarate'], m['rssi'], m['snr']))

    def cnt_level(self, match):
        """ level based classification """
        level = match['level'] if match else None
        if not level: level = 'n/a'
        self.stat_count('level', level)

    def cnt_facility(self, match):
        """ level based classification """
        facility = match['facility'] if match else None
        if not facility: facility = 'n/a'
        self.stat_count('facility', facility)

    def cnt_pushpull(self, match):
        """ PUSH_DATA and PULL_DATA"""
        regex = self.cfg.get('data')
        if regex is None: return
        facility = match['facility']
        regex = regex.get(facility)
        if regex is None: return
        m = regex.search(match['msg'])
        if not m: return
        self.stat_count('data', m['pushpull'])

    def classify(self, line):
        """ classify the log line """
        regex = self.cfg.get('line')
        # passtrough - no classification
        if regex is None: return
        #
        m = regex.match(line)
        # level
        self.cnt_level(m)
        # facility
        self.cnt_facility(m)
        # data push / pull
        self.cnt_pushpull(m)
        # detail rf
        self.stat_detail_rf(m)
        # stat msg level
        #self.stat_count(m['level'], self.cnt)
        # stat calls
        #self.stat_count(m['call'],  self.call)
        # call
        #self.stat_rf(m)

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
    print('DATA:'); print(c.cnt['data'])
    print('=')
    print('FACILITY:'); print(c.cnt['facility'])
    print('=')
    print('RF:');
    c.print_table(c.detail['rf'])
    print('=')
