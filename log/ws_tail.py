#!/usr/bin/python3
#
# utility to tail remote log files via websocket ws:// connection
#
# requires: sudo pip3 install websocket-client # https://github.com/websocket-client/websocket-client
#
#

# for tail --follow console.log (long par version) use:
# ws_tail.py --follow console.log ws://controllinohotspot
#
# for tail -f error.log (short par version) use:
# ws_tail.py -f err controllinohotspot

import websocket
import urllib.request
import json
import argparse
import sys
import time, datetime

__VERSION__ = '2022.07.05'

# miner config
#
MINER = {
    'controllino': {
        'dashboard': '1.3.5',
        'console.log': {
            'open': 'initconsolelog/console',
            'port': 7878
        },
        'error.log': {
            'open': 'initconsolelog/error',
            'port': 7879
        },
        # broken since fw 1.3.4
        'process.log': {
            'open': 'processlog'
        },
    }
}

# debog cmponents (csv)
#
DBGMODE = ''

def dbg(component, msg):
    """ print dbg msg if requested in global DBGMODE """
    if component not in DBGMODE: return
    print('= DBG =', datetime.datetime.now().strftime('%Y-%d-%m %H:%M:%S'), '=', component, '=', msg)


class WSClient:

    def __init__(self, host, logname, minercfg, ping):
        """ init """
        self.miner_cfg = minercfg
        self.ws_server = self.ws_host(host)
        self.follow    = self.log_name(logname)
        self.ping      = self.ping_par(ping)

    def ws_host(self, host, proto='ws'):
        """ add protocol/scheme to the host if not already there """
        return host if host.startswith(proto) else '%s://%s' % (proto, host)

    def log_name(self, logname):
        """ set full logname from shorted version: err -> error.log """
        if logname.startswith('con'): return 'console.log'
        if logname.startswith('err'): return 'error.log'
        return logname

    def ping_par(self, pingcsv):
        """ x """
        val = pingcsv.split(',')
        return {
            'ping_interval': int(val[0]) if len(val) >= 1 else  0,
            'ping_timeout':  int(val[1]) if len(val) >= 2 else 10,
            'ping_payload':  val[2] if len(val) >= 3 else 'alive?'
        }

    def log_init(self, tries=10, sleep=5):
        """ initialize websocket via http - controllino specific """
        url = ''.join([ self.ws_server.replace('ws','http'), '/', self.miner_cfg[self.follow]['open'] ])
        for attempt in range(1, tries+1):
            try:
                with urllib.request.urlopen(url) as u:
                    rs = u.read()
                dbg('tl', 'log_init() attempt %d: %s -> %s' % (attempt, url, rs))
                # {"status":200}
                code = json.loads(rs).get('status')
                return code == 200
            except urllib.error.URLError as e:
                # urllib.error.URLError: <urlopen error [Errno 111] Connection refused>
                dbg('tl', '= ERR = log_init() attempt %d = %s' % (attempt, e.reason))
                time.sleep(sleep)

    def on_message(self, ws, message):
        #print(self.loop, message)
        print(message)

    def on_error(self, ws, exc):
        """ = ERR = Connection to remote host was lost. = """
        dbg('tl', '= ERR = %s = %s' % (exc, ws.url))

    def on_close(self, ws, close_status_code, close_msg):
        if not close_status_code: close_status_code = '?'
        if not close_msg: close_msg = '?'
        dbg('tl', "websocket connection closed = [ %s ] %s" % (close_status_code, close_msg))

    def on_open(self, ws):
        dbg('tl', "websocket connection opened = %s" % ws.url)

    def on_ping(self, ws, message):
        dbg('tl', "ping received = %s" % message)

    def on_pong(self, ws, message):
        dbg('tl', "pong received = %s" % message)
        #self.log_init()

    def run(self, maxloops=10):
        """ open logfile and loop forever """
        wsurl = '%s:%d' % (self.ws_server, self.miner_cfg.get(self.follow).get('port'))
        for self.loop in range(1, maxloops+1):
            dbg('tl', '=== loop: %d ===' % self.loop)
            if not self.log_init(): break
            ws = websocket.WebSocketApp(wsurl,
                                    on_open=self.on_open,
                                    on_ping=self.on_ping,
                                    on_pong=self.on_pong,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
            # ^C= ERR =  = ws://controllinohotspot:7878, teardown= False
            # = ERR = Connection to remote host was lost. = ws://controllinohotspot:7878, teardown= True
            # break only on CRTL-C and not on ws errors
            if not ws.run_forever(ping_interval=self.ping['ping_interval'],
                                  ping_timeout =self.ping['ping_timeout'],
                                  ping_payload =self.ping['ping_payload']):
                break
            # send close status back - https://datatracker.ietf.org/doc/html/rfc6455#section-7.4
            ws.close(status=websocket.STATUS_PROTOCOL_ERROR)
        # === loop: 9 = ERR = [Errno 111] Connection refused = ws://controllinohotspot:7878
        dbg('tl', '=== loop end = loop %d of maxloop %d ===' % (self.loop, maxloops))

if __name__ == "__main__":
    # cli pars
    parser = argparse.ArgumentParser(description='tail remote log from host/miner via websocket connection ver %s' % __VERSION__,
                                     epilog='example: ws_tail.py -f console.log controllinohotspot')
    parser.add_argument('wserver', metavar='[ws[s]://]host',
                        help='websocket server to connect to')
    parser.add_argument('-f', '--follow', metavar='name', required=True,
                        help='follow log name (con[sole[.log]] or err[or[.log]])')
    parser.add_argument('-p', '--ping',  metavar='int[,tout]', default='', required=False,
                        help='enable periodic ping with interval int seconds and timeout tout seconds')
    parser.add_argument('-d', '--debug',  metavar='c1[,c2]', default='', required=False,
                        help='enable debug for component (par for pars, tl for tail, ws for websocket)')
    args = parser.parse_args()
    DBGMODE = args.debug
    if 'ws' in DBGMODE: websocket.enableTrace(True)
    websocket.setdefaulttimeout(30)

    # show usage if no args given
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # websocket client
    wsc = WSClient(host=args.wserver, logname=args.follow, minercfg=MINER['controllino'], ping=args.ping)
    # open log and run websocket forever
    wsc.run()

