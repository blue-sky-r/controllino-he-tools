#!/bin/bash

# For CONTROLLINO miner only - https://hotspot.controllino.com/
#  firmware_version: raspbian bionic 2022.03.23.1 + dashboard 1.2.1 - 1.3.4
#  firmware_version: raspbian bionic 2022.04.27.0 - 2022.05.13.0 + dashboard 1.3.5
#  firmware_version: raspbian bionic 2022.05.19.0 - 2022.06.01.0 + dashboard 1.3.6
#  firmware_version: raspbian bionic 2022.07.14.0 - 2022.08.02 + dashboard 1.3.7 - 1.3.9
#  firmware_version: raspbian bionic 2022.10.28.0 + dashboard 1.4.2

# about
#
_about_="mrtg probe to graph He miner disk/cpu usage/load"

# version
#
_version_="2022.11.18"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-load.sh"

# DEFAULT He miner hostname
#
host="controllinohotspot"

# json message keys to display in this order
#
keys="diskusage, cpuload"

# in case of error, output this value for mrtg (otherwise mrtg will use http errro code as value)
#
errval=0

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

usage: $0 [-h] [-d] [host]

-h   ... show this usage help
-d   ... additional debug info
host ... host/miner to connect to (default $host)

$_github_
""" && exit 1

# optional debug
#
[ "$1" == "-d" ] && DBG=1 && shift

# optional He miner hostname
#
[ $1 ] && host=$1

# url to connect to
#
url=http://$host/hotspotstats

[ $DBG ] && echo "DBG.URL: $url"

# json response
#
json=$( wget $opts $url ); excode=$?

# {"data":{"type":"systemstat","attributes":{"diskusage":"58%","ramusage":"403","cpuload":"2%","cputemp":"52.09"}}}
[ $DBG ] && echo "DBG.WGET.exitcode: $excode" && echo "DBG.JSON: $json" && echo "DBG.KEYS: $keys" && echo

# python code to process json
#
pycode=$( cat <<___
import sys,json
try: j = json.loads(r'$json')
except json.decoder.JSONDecodeError: j = {}
attr = j.get('data',{}).get('attributes')
if not attr:
    print($errval, 'json:', j)
    print($errval, 'data:', j.get('data', 'wget-exitcode %d' % $excode))
else:
    for key in '$keys'.split(', '):
        if '$DBG': print('DBG.key:', key, end=' => ')
        print(attr.get(key).replace('%',''))
if '$DBG': print('DBG.UPTIME:', end=' ')
print('?')
if '$DBG': print('DBG.HOST:', end=' ')
print('$host')
___
)

# execute
#
$python -c "$pycode"
