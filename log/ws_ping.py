#!/usr/bin/python3
#
# websocket ping

__version__ = '2022.05.22'

import datetime
import argparse
import websocket
import re


DEFAULTS = {
    'datetime': '%Y-%d-%m %H:%M:%S',
    'interval': 1,
    'payload': 'ping-pong',
    'wait': 0.9,
    'timeout': 10
}


class Ws_ping:

    def __init__(self, args):
        """ """
        self.url = args.url
        self.audible = args.audible
        self.count = args.count
        self.datefmt = args.datetime
        self.interval = args.interval
        self.payload = args.payload
        self.wait = args.wait
        self.timeout = args.timeout
        self.verbose = args.verbose
        self.debug = args.debug
        self.seq = 1
        self.stat = { 'min': 9999, 'max': 0, 'recok': 0, 'recerr': 0, 'sum': 0 }

    def now_ymd_hms(self):
        return datetime.datetime.now().strftime(self.datefmt)

    def on_open(self, wsapp):
        if self.verbose: print("OPEN %s" % wsapp.url)

    def on_close(self, wsapp, close_status_code, close_msg):
        if not close_status_code: close_status_code = '?'
        if not close_msg: close_msg = '?'
        if self.verbose: print("CLOSE websocket connection = [ %s ] %s" % (close_status_code, close_msg))

    def on_error(self, wsapp, err):
        # = ERR = ping/pong timed out = ws://controllinohotspot:7878
        self.stat['recerr'] += 1
        if self.verbose: print('= ERR = %s = %s' % (err, wsapp.url))
        print(self.now_ymd_hms(), "pong seq# %d error %s" % (self.seq, err))
        self.seq += 1

    def on_message(self, wsapp, message):
        if self.verbose: print(message)

    def on_ping(self, wsapp, message):
        if self.verbose: print("PING received")

    def on_pong(self, wsapp, message):
        """ pong replay received """
        round_time_ms = (wsapp.last_pong_tm - wsapp.last_ping_tm) * 1000
        self.update_stats(round_time_ms)
        print(self.now_ymd_hms(), "pong seq# %d received in %.2f ms" % (self.seq, round_time_ms))
        if self.count and self.seq >= self.count:
            wsapp.keep_running = False
        self.seq += 1

    def update_stats(self, val):
        """ update min/max/avg statistics """
        self.stat['min'] = self.stat['min'] if self.stat['min'] < val else val
        self.stat['max'] = self.stat['max'] if self.stat['max'] > val else val
        self.stat['sum'] += val
        self.stat['recok'] += 1

    def print_stats(self):
        """ final statistics """

        def percent(part, whole):
            if part == 0: return 0
            return part / whole * 100

        def hms(ms):
            """ 1232ms -> 1h 2m 3s 43ms """
            unit = {
                'd': 86400E3,
                'h': 3600E3,
                'm': 60E3,
                's': 1E3,
                'ms': 1
            }
            hs = []
            for j,mult in unit.items():
                if ms < mult: continue
                k = ms // mult
                hs.append("%d%s" % (k,j))
                ms -= k * mult
            return ' '.join(hs)

        # --- controllinohotspot.local ping statistics ---
        print('--- %s websocket ping statistics ---' % self.url)
        # 10 packets transmitted, 10 received, 0% packet loss, time 9013ms
        sent = self.stat['recok'] + self.stat['recerr']
        print("%d pings sent, %d pongs received, %.2f%% packet loss, total rtt is %s" %
              (sent, self.stat['recok'], 100 - percent(self.stat['recok'], sent), hms(self.stat['sum'])))
        # rtt min/avg/max/mdev = 0.034/0.035/0.037/0.001 ms
        print("rtt min/avg/max/sum = %.3f/%.3f/%.3f/%.3f ms" %
              (self.stat['min'], self.stat['sum']/self.stat['recok'] if self.stat['recok']>0 else 1, self.stat['max'], self.stat['sum']))

    def run(self):
        """ """
        websocket.enableTrace(self.debug)
        websocket.setdefaulttimeout(self.timeout)
        wsapp = websocket.WebSocketApp(self.url,
                                       on_open=self.on_open, on_close=self.on_close,
                                       on_error=self.on_error,
                                       on_message=self.on_message,
                                       on_ping=self.on_ping, on_pong=self.on_pong)
        while self.stat['recok'] + self.stat['recerr'] < self.count:
            wsapp.run_forever(ping_interval=self.interval,
                          ping_timeout=self.wait,
                          ping_payload=self.payload)
        # stats
        self.print_stats()


def parse_args():
    """ parse cli pars """

    def valid_url(arg_value, pat=re.compile(r'wss?://\w+(\.\w+)*(:\d+)?')):
        """ ws[s]://host[:port] """
        if not pat.match(arg_value):
            raise ValueError
        return arg_value

    # https://docs.python.org/3/library/argparse.html#module-argparse
    parser = argparse.ArgumentParser(description="WebSocket ping vesrion %s" % __version__,
                                     epilog="example: ws_ping -c 100 ws://controllinohotspot:7878",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("url", metavar="ws_url", type=valid_url,
                        help="destination websocket url. ex. ws://host.domain:port")
    parser.add_argument("-a", "--audible", action='store_true',
                        help="audible ping (bel)")
    parser.add_argument("-c", "--count", metavar="limit", default=0, type=int,
                        help="send only limited count of ping probes, 0 for unlimited")
    parser.add_argument("-D", "--datetime", metavar='"format"', default=DEFAULTS.get('datetime'),
                        help="format string for timestamps")
    parser.add_argument("-i", "--interval", metavar="secs", type=int, default=DEFAULTS.get('interval'),
                        help="seconds between sending each packet")
    parser.add_argument("-p", "--payload", metavar='"string"', type=str, default=DEFAULTS.get('payload'),
                        help="contents of payload")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet output")
    parser.add_argument("-v", "--verbose", action='store_true',
                        help="websock verbose output")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="websock debug output")
    parser.add_argument("-w", "--wait", metavar="secs", type=float, default=DEFAULTS.get('wait'),
                        help="pong reply wait timeout, must be lower than interval")
    parser.add_argument("-W", "--timeout", metavar="secs", type=float, default=DEFAULTS.get('timeout'),
                        help="global socket timeout")
    return parser.parse_args()


args = parse_args()
wsp = Ws_ping(args)
wsp.run()


