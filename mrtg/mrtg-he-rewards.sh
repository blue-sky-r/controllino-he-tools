#!/bin/bash

# For CONTROLLINO miner only - https://hotspot.controllino.com/
#  firmware_version: raspbian bionic 2022.03.23.1 + dashboard 1.2.1 - 1.3.4
#  firmware_version: raspbian bionic 2022.04.27.0 - 2022.05.13.0 + dashboard 1.3.5

# about
#
_about_="mrtg probe to graph He miner rewards"

# version
#
_version_="2022.05.15"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-rewards.sh"

# DEFAULT He miner hostname
#
host="controllinohotspot"

# DEFAULT time range for rewards: 1/7/14 days
#
days=1

# multiplication koeff to get integer
#
km='1E3'

# json response keys to expressions to eveluate to display in this order
#
keys="total * $km, avg * $km"

# wget options
#
opts="--retry-on-host-error --retry-connrefused --retry-on-http-error=503 --timeout=7 --tries=3 -q -O -"

# python interpreter
#
python="python3"

# usage help
#
[ "$1" == "-h" ] && cat <<< """
= $_about_ = ver $_version_ =

usage: $0 [-h] [-d] [host [days]]

-h   ... show this usage help
-d   ... additional debug info
host ... host/miner to connect to (default $host)
days ... reward interval to query in days, valid values are 1,7,14 (default $days)

$_github_
""" && exit 1

# optional debug
#
[ "$1" == "-d" ] && DBG=1 && shift

# optional He miner hostname
#
[ $1 ] && host=$1

# optional rewards period
#
[ $2 ] && days=$2

# url to connect to
#
url=http://$host/rewards/$days

[ $DBG ] && echo "DBG.URL: $url"

# get json response
#
json=$( wget $opts $url ); excode=$?

# {"status":200,"rewards":{"total":0.31404812,"sum":31404812,"stddev":0.012765751345,"min":0,"median":0.01125426,"max":0,"avg":0.0125619248}}
[ $DBG ] && echo "DBG.WGET.exitcode: $excode" && echo "DBG.JSON: $json" && echo "DBG.KEYS: $keys" && echo

# python code to process json
#
pycode=$( cat <<___
import sys,json
try: j = json.loads(r'$json')
except json.decoder.JSONDecodeError: sys.exit(-1)
if j.get('status') != 200:
    print('status:', j.get('status'))
    print('message:', j.get('message'))
else:
    vars = j.get('rewards')
    for key in '$keys'.split(', '):
        if '$DBG': print('DBG.key:', key, end=' => ')
        v = eval(key, vars)
        print(round(v))
if '$DBG': print('DBG.UPTIME:', end=' ')
print('?')
if '$DBG': print('DBG.HOST:', end=' ')
print('$host')
___
)

# execute
#
$python -c "$pycode"
