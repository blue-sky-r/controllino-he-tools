#!/usr/bin/python3
#
# utility to retrieve log files via websocket ws:// connection
#
# requires: sudo pip3 install websocket-client
#

# console.log:
# ws_read.py ws://controllinohotspot:7878
#
# error.log:
# ws_read.py ws://controllinohotspot:7879

import websocket
import argparse


def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print('= ERR =',error)

def on_close(ws, close_status_code, close_msg):
    print("= WebSocket connection closed =")

def on_open(ws):
    print("= WebSocket connection opened =")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='websocket log retrieval')
    parser.add_argument('wserver', metavar='ws://host:port', help='websocket server to connect to')
    parser.add_argument('-d', '--debug', required=False, help='enable debug for component (ws)')
    args = parser.parse_args()

    # websocket debug
    if args.debug and 'ws' in args.debug: websocket.enableTrace(True)

    ws = websocket.WebSocketApp(args.wserver,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    ws.run_forever()
