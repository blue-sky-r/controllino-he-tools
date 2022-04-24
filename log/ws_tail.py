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

__VERSION__ = '2022.04.23'

# miner config
#
MINER = {
    'controllino': {
        'fw': '1.3.1',
        'console.log': {
            'open': 'initconsolelog/console',
            'port': 7878,
        },
        'error.log': {
            'open': 'initconsolelog/error',
            'port': 7879,
        },
        'process.log': {
            'open': 'processlog'
        },
        'classify': {
            'line': re.compile(r'^(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \d \[(?P<level>\w+)\] <[\d.]+>@(?P<proc>\w+:\w+):\{\d+,\d+\} (?P<msg>.+)$')
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
        self.stat = {}

    def stat_count(self, level, proc):
        """ [level][proc] """
        self.stat[level] = 1 + self.stat.get(level, 0)

    def stat_error(self, msg):
        """ """
        regex = self.cfg['console.log']['split']
        m = regex.split(msg)

    def classify(self, msg):
        """ classify the msg """
        regex = self.cfg.get('line')
        if regex is None: return
        m = regex.match(msg)
        #if m is None: return
        self.stat_count(m['level'], m['proc'])
        #if m['level'] == 'error':
        #    self.stat_error(m['msg'])


class WSClient:

    def __init__(self, host, logname, minercfg):
        self.miner_cfg = minercfg
        self.ws_server = self.ws_host(host)
        self.follow    = self.follow_log(logname)
        self.classifier =  Classifier(minercfg.get('classify'))

    def ws_host(self, host, proto='ws'):
        """ add protocol/scheme to the host if not already there """
        return host if host.startswith(proto) else '%s://%s' % (proto, host)

    def follow_log(self, logname):
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
                print('= ERR = log_init() attempt %d = [code: %s] %s' % (attempt, e.code, e.reason))
                time.sleep(sleep)

    def on_message(self, ws, message):
        print(self.loop, message)
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
        """ kill -USR1 pid """
        print("=== statistics === signum:",signum,' frame:',frame)
        print('f_globals:',frame.f_globals)
        print('f_locals:',frame.f_locals)
        print(self.classifier.stat)

    def run(self):
        """ open logfile and loop forever """
        wsurl = '%s:%d' % (self.ws_server, self.miner_cfg.get(self.follow).get('port'))
        for self.loop in range(1,3):
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
    # open log and run websocket forever
    wsc.run()
