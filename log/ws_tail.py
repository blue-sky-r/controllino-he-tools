#!/usr/bin/python3
#
# utility to tail remote log files via websocket ws:// connection
#
# requires: sudo pip3 install websocket-client
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
        }
    }
}

# debog cmponents (csv)
#
DBGMODE = ''

def dbg(component, msg):
    """ print dbg msg if requested in global DBGMODE """
    if component not in DBGMODE: return
    print('= DBG =', component, '=', msg)


class WSClient:

    def __init__(self, host, logname, minercfg):
        self.miner_cfg = minercfg
        self.ws_server = self.ws_host(host)
        self.follow    = self.follow_log(logname)

    def ws_host(self, host, proto='ws'):
        """ add protocol/scheme to the host if not already there """
        return host if host.startswith(proto) else '%s://%s' % (proto, host)

    def follow_log(self, logname):
        """ set full logname from shorted version: err -> error.log """
        if logname.startswith('con'): return 'console.log'
        if logname.startswith('err'): return 'error.log'
        return logname

    def log_init(self):
        """ initialize websocket via http - controllino specific """
        url = ''.join([ self.ws_server.replace('ws','http'), '/', self.miner_cfg[self.follow]['open'] ])
        with urllib.request.urlopen(url) as u:
            rs = u.read()
        dbg('ws', 'load_init() %s -> %s' % (url, rs))
        # {"status":200}
        code = json.loads(rs).get('status')
        return code == 200

    def on_message(self, ws, message):
        print(message)

    def on_error(self, ws, error):
        """ = ERR = Connection to remote host was lost. = """
        print('= ERR =',error,'=',ws.url)

    def on_close(self, ws, close_status_code, close_msg):
        if close_status_code and close_msg:
            print("= websocket connection closed = [ %d ] %s" % (close_status_code, close_msg))

    def on_open(self, ws):
        print("= websocket connection opened =", ws.url)

    def run(self):
        """ open logfile and loop forever """
        if not self.log_init(): return
        wsurl = '%s:%d' % (self.ws_server, self.miner_cfg.get(self.follow).get('port'))
        ws = websocket.WebSocketApp(wsurl,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.run_forever()

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
    # open log and run websocket forever
    wsc.run()
