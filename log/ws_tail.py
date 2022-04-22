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

def ws_host(host, proto='ws'):
    """ add protocol/scheme to the host if not already there """
    return host if host.startswith(proto) else 'ws://%s' % host

def log_init(wshost, logname):
    """ initialize websocket via http - controllino specific """
    url = ''.join([wshost.replace('ws','http'), '/', MINER['controllino'].get(logname).get('open')])
    with urllib.request.urlopen(url) as u:
        rs = u.read()
    dbg('ws', 'log_open %s -> %s' % (url, rs))
    # {"status":200}
    code = json.loads(rs).get('status')
    dbg('ws', 'log_open status code: %s' % code)
    return code == 200

def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print('= ERR =',error,'=')

def on_close(ws, close_status_code, close_msg):
    print("= websocket connection closed = code:",close_status_code,'=',close_msg)

def on_open(ws):
    print("= websocket connection opened =", ws.url)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='tail remote log from host via websocket connection',
                                     epilog='example: ws_tail.py -f console.log controllinohotspot')
    parser.add_argument('wserver',  metavar='[ws[s]://]host', help='websocket server to connect to')
    parser.add_argument('-f', '--follow',   metavar='name', default='', required=False, help='follow log name (con[sole[.log]] or err[or[.log]])')
    parser.add_argument('-d', '--debug', metavar='c1[,c2]', default='', required=False, help='enable debug for component (par for pars, ws for websocket, ql for qualifier)')
    args = parser.parse_args()
    wserver = ws_host(args.wserver)
    DBGMODE = args.debug
    follow   = args.follow
    if follow.startswith('con'): follow = 'console.log'
    if follow.startswith('err'): follow = 'error.log'
    dbg('par', 'follow=%s, debug=%s, wserver=%s' % (follow, DBGMODE, wserver))

    if 'ws' in DBGMODE: websocket.enableTrace(True)
    # open log and run websocket forever
    if log_init(wserver, follow):
        wsurl = '%s:%d' % (wserver, MINER['controllino'].get(follow).get('port'))
        ws = websocket.WebSocketApp(wsurl,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
        ws.run_forever()
