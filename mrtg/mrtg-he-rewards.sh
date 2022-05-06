#!/bin/bash

# FOR: CONTROLLINO miner only
#  firmware_version: raspbian bionic 2022.03.23.1 + dashboard 1.2.1 - 1.3.4
#  firmware_version: raspbian bionic 2022.04.19.1 + dashboard 1.3.5

# about
#
_about_="mrtg probe to graph He miner rewards"

# version
#
_version_="2022.05.06"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-rewards.sh"

# DEFAULT He miner hostname
#
host="controllinohotspot"

# DEFAULT time range for rewards: 1/7/14 days
#
days=1

# json message keys and multipliers to display in this order, format ("key",mult),("key2",mult2)...
#
keys='("sum",1),("avg",1E9)'

# wget options
#
opts="--retry-on-host-error --retry-connrefused --retry-on-http-error=503 --timeout=7 --tries=3 -q -O -"

# python interpreter
#
python="python3"

# usage help
#
[ "$1" == "-h" ] && cat <<< """
= $_about_ = ver $_version_ = $_github_ =

usage: $0 [-h] [-d] [host [days]]

-h   ... show this usage help
-d   ... additional debug info
host ... host/miner to connect to (default $host)
days ... reward interval to query in days, valid values are 1,7,14 (default $days)
""" && exit 1

# optional debug
#
[ "$1" == "-d" ] && DBG=1 && shift

# o[tional He miner hostname
#
[ $1 ] && host=$1

# optional rewards period
#
[ $2 ] && days=$2

# url to connect to
#
url=http://$host/rewards/$days

# json response
#
json=$( wget $opts $url )

# debug output
#
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
for key,mult in ($keys):
    print(round(r.get(key,0) * mult))
print('?')
print('$host')
___
)

# execute
#
$python -c "$pycode"
