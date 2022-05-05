#!/bin/bash

# usage help
#
[ "$1" == "-h" ] && cat <<< """
= mrtg probe to graph He rewards =

usage: $0 [-h] [-d] [host [rewards]]

-h     ... show this usage help
-d     ... additional debug info
host   ... host to connect to (default controllinohotspot)
reward ... reward interval to query (default 1day = 24h)
""" && exit 1

# debug
#
[ "$1" == "-d" ] && DBG=1 && shift

# He miner hostname
#
host=${1:-controllinohotspot}

# time range for rewards: 1/7/14 days
#
rewards=${2:-1}

# json message keys to display in this order
#
keys="height,sync height,uptime,miner name"

# wget options
#
opts="--retry-on-host-error --retry-connrefused --retry-on-http-error=503 --timeout=7 --tries=3 -q -O -"

# url to connect to
#
url=http://$host/rewards/$rewards

# json response
#
json=$( wget $opts $url )

[ $DBG ] && echo "DBG.URL: $url" && echo "DBG.JSON: $json" && echo

# {"status":200,"rewards":{"total":0.31404812,"sum":31404812,"stddev":0.012765751345,"min":0,"median":0.01125426,"max":0,"avg":0.0125619248}}

# python code to process json
#
pycode=$( cat <<___
import sys,json
try:
  j = json.loads(r'$json')
except json.decoder.JSONDecodeError:
  sys.exit(-1)
if j.get('status') != 200: sys.exit(-1)
r = j.get('rewards')
print(r.get('sum'))
print(round(r.get('avg') * 10E8))
print('?')
print('$host')
___
)

python3 -c "$pycode"
