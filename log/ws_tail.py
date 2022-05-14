#!/usr/bin/python3
#
# utility to tail remote log files via websocket ws:// connection
#
# requires: sudo pip3 install websocket-client # https://github.com/websocket-client/websocket-client
#

# tail --follow console.log (long par version):
# ws_tail.py --follow console.log ws://controllinohotspot
#
# tail -f error.log (short par version):
# ws_tail.py -f err controllinohotspot

import websocket
import urllib.request
import json
import argparse
import re
import signal
import time

__VERSION__ = '2022.05.14'

# miner config
#
MINER = {
    'controllino': {
        'fw': '1.3.5',
        'console.log': {
            'open': 'initconsolelog/console',
            'port': 7878
        },
        'error.log': {
            'open': 'initconsolelog/error',
            'port': 7879
        },
        'process.log': {
            'open': 'processlog'
        },
        'classify': {
            'console.log': {
                # 2022-04-28 20:24:07.116 7 [notice] <0.12157.58>@libp2p_yamux_session:handle_info:{189,5} Session liveness failure
                'line': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d '
                                   '\[(?P<level>\w+)\] '
                                   '<[\d.]+>@(?P<call>\w+:\w+):\{(?P<loc>\d+,\d+)\} '
                                   '(?P<msg>.+)$'),
            },
            'error.log': {
                # 2022-05-12 13:49:40.460 [error] <0.32357.0>@libp2p_stream_relay:handle_server_data:{193,13} fail to pass request
                'line': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) '
                                   '\[(?P<level>\w+)\] '
                                   '<[\d.]+>@(?P<call>\w+:\w+):\{(?P<loc>\d+,\d+)\} '
                                   '(?P<msg>.+)$'),
            },
        }
    }
}

# 'line': re.compile(
#    r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d \[(?P<level>\w+)\] <[\d.]+>@(?P<proc>\w+:\w+):\{\d+,\d+\} (?P<msg>.+)$'),
# 'error': 'failed to '

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
        self.cnt = {}
        self.call = {}

    def stat_count(self, key, counter):
        """ cnt[key]++ """
        counter[key] = 1 + counter.get(key, 0)

    def classify(self, msg):
        """ classify the msg """
        regex = self.cfg.get('line')
        if regex is None: return
        m = regex.match(msg)
        #if m is None: return
        # stat msg level
        self.stat_count(m['level'], self.cnt)
        # stat calls
        self.stat_count(m['call'],  self.call)


class WSClient:

    def __init__(self, host, logname, minercfg):
        self.miner_cfg = minercfg
        self.ws_server = self.ws_host(host)
        self.follow    = self.log_name(logname)
        self.classifier =  Classifier(minercfg['classify'].get(self.follow))

    def ws_host(self, host, proto='ws'):
        """ add protocol/scheme to the host if not already there """
        return host if host.startswith(proto) else '%s://%s' % (proto, host)

    def log_name(self, logname):
        """ set full logname from shorted version: err -> error.log """
        if logname.startswith('con'): return 'console.log'
        if logname.startswith('err'): return 'error.log'
        return logname

    def log_init(self, tries=10, sleep=5):
        """ initialize websocket via http - controllino specific """
        url = ''.join([ self.ws_server.replace('ws','http'), '/', self.miner_cfg[self.follow]['open'] ])
        for attempt in range(1, tries+1):
            try:
                with urllib.request.urlopen(url) as u:
                    rs = u.read()
                dbg('ws', 'load_init() attempt %d: %s -> %s' % (attempt, url, rs))
                # {"status":200}
                code = json.loads(rs).get('status')
                return code == 200
            except urllib.error.URLError as e:
                # urllib.error.URLError: <urlopen error [Errno 111] Connection refused>
                print('= ERR = log_init() attempt %d = %s' % (attempt, e.reason))
                time.sleep(sleep)

    def on_message(self, ws, message):
        #print(self.loop, message)
        print(message)
        self.classifier.classify(message)
        #print(self.classifier.stat)

    def on_error(self, ws, exc):
        """ = ERR = Connection to remote host was lost. = """
        print('= ERR =',exc,'=',ws.url)

    def on_close(self, ws, close_status_code, close_msg):
        if close_status_code and close_msg:
            print("= websocket connection closed = [ %d ] %s" % (close_status_code, close_msg))

    def on_open(self, ws):
        print("= websocket connection opened =", ws.url)

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

    def run(self, ):
        """ open logfile and loop forever """
        wsurl = '%s:%d' % (self.ws_server, self.miner_cfg.get(self.follow).get('port'))
        for self.loop in range(1, 10):
            print('=== loop:',self.loop)
            if not self.log_init(): break
            ws = websocket.WebSocketApp(wsurl,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
            if not ws.run_forever(): break
            # ^C= ERR =  = ws://controllinohotspot:7878, teardown= False
            # = ERR = Connection to remote host was lost. = ws://controllinohotspot:7878, teardown= True
        print('=== loop end ===')
        # === loop: 2 = ERR = [Errno 111] Connection refused = ws://controllinohotspot:7878
        # === loop: 9 = ERR = [Errno 111] Connection refused = ws://controllinohotspot:7878

if __name__ == "__main__":
    # cli pars
    parser = argparse.ArgumentParser(description='tail remote log from host via websocket connection',
                                     epilog='example: ws_tail.py -f console.log controllinohotspot')
    parser.add_argument('wserver',  metavar='[ws[s]://]host', help='websocket server to connect to')
    parser.add_argument('-f', '--follow',   metavar='name', default='', required=False, help='follow log name (con[sole[.log]] or err[or[.log]])')
    parser.add_argument('-d', '--debug', metavar='c1[,c2]', default='', required=False, help='enable debug for component (par for pars, ws for websocket, ql for qualifier)')
    args = parser.parse_args()
    DBGMODE = args.debug
    if 'ws' in DBGMODE: websocket.enableTrace(True)

    # websocket client
    wsc = WSClient(host=args.wserver, logname=args.follow, minercfg=MINER['controllino'])
    # signals
    signal.signal(signal.SIGUSR1, wsc.on_usr1)
    signal.signal(signal.SIGUSR2, wsc.on_usr2)
    # open log and run websocket forever
    wsc.run()
