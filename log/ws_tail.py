#!/usr/bin/python3
#
# utility to tail remote log files via websocket ws:// connection
#
# requires: sudo pip3 install websocket-client # https://github.com/websocket-client/websocket-client
#
# Note: retrieving controllino miner log keeps dying silently while websocket connection is alive (responding to ping-pong)
# so there is a trick with counting log messages (lines) between pings. If number of received messages between two
# pings is zero, websocket connection is closed and reopened again (this trick works well so far for controllino)
#

# for tail --follow console.log and ping/pong each 90sec with 5sec timeout (long par version) use:
# ws_tail.py --follow console.log --ping 90,5 ws://controllinohotspot
#
# for tail -f error.log without ping/pong (short par version) use:
# ws_tail.py -f err controllinohotspot
#

import websocket
import urllib.request
import json
import argparse
import sys
import time, datetime

__VERSION__ = '2022.07.24'

# miner config
#
MINER = {
    'controllino': {
        'dashboard': '1.3.9',
        'ping_defaults': {
            'ping_interval': 0,
            'ping_timeout': 10,
            'ping_payload': 'alive?'
        },
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
        """ process comma separated ping cli string pars interval,timeout,payload """
        ping = self.miner_cfg['ping_defaults']
        # actual values
        parsd = dict([ (k,int(v) if v.isnumeric() else v) for k,v in zip(ping.keys(), pingcsv.split(',')) if v != '' ])
        ping.update(parsd)
        return ping

    def log_init(self, tries=10, sleep=5):
        """ initialize websocket via http - controllino specific """
        self.lines = 0
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
                dbg('tl', 'ERR = log_init() attempt %d = %s' % (attempt, e.reason))
                time.sleep(sleep)

    def ws_close(self, ws, status=websocket.STATUS_NORMAL):
        """ close websocket connection with status """
        dbg('tl', 'ws_close() with status %d' % status)
        ws.close(status=status)

    def on_message(self, ws, message):
        self.lines += 1
        print(message)

    def on_error(self, ws, exc):
        """ = ERR = Connection to remote host was lost. = """
        dbg('tl', 'ERR = %s = %s' % (exc, ws.url))

    def on_close(self, ws, close_status_code, close_msg):
        if not close_status_code: close_status_code = '?'
        if not close_msg: close_msg = '?'
        dbg('tl', "websocket connection closed = [ %s ] %s" % (close_status_code, close_msg))

    def on_open(self, ws):
        dbg('tl', "websocket connection opened = %s" % ws.url)

    def on_ping(self, ws, message):
        dbg('tl', "ping received = %s" % message)

    def on_pong(self, ws, message):
        dbg('tl', "pong received = %s = %d messages since the last pong =" % (message, self.lines))
        lines = self.lines
        self.lines = 0
        if lines == 0:
            self.ws_close(ws, status=websocket.STATUS_NORMAL)
            self.run()

    def run(self, limit=5):
        """ open logfile and loop forever """
        wsurl = '%s:%d' % (self.ws_server, self.miner_cfg.get(self.follow).get('port'))
        for self.loop in range(1, limit+1):
            if not self.log_init(): break
            dbg('tl', "start of loop %d / %d =" % (self.loop, limit))
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
                              ping_payload =self.ping['ping_payload']): break
            # send close status back - https://datatracker.ietf.org/doc/html/rfc6455#section-7.4
            self.ws_close(ws, status=websocket.STATUS_PROTOCOL_ERROR)
        dbg('tl', "end of loop %d / %d =" % (self.loop, limit))

if __name__ == "__main__":
    # cli pars
    parser = argparse.ArgumentParser(description='tail remote log from host/miner via websocket connection ver %s' % __VERSION__,
                                     epilog='example: ws_tail.py -f console.log controllinohotspot')
    parser.add_argument('wserver', metavar='[ws[s]://]host',
                        help='websocket server to connect to')
    parser.add_argument('-f', '--follow', metavar='name', required=True,
                        help='follow log name (con[sole[.log]] or err[or[.log]])')
    parser.add_argument('-p', '--ping',  metavar='int[,tout[,payload]]', default='', required=False,
                        help='enable periodic ping with interval int seconds and timeout tout seconds with string payload')
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

