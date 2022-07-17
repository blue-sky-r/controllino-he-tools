#!/bin/bash

# For CONTROLLINO miner only - https://hotspot.controllino.com/
#  firmware_version: raspbian bionic 2022.07.14.0 + dashboard 1.3.7

# about
#
_about_="mrtg probe to graph He miner General Witnesses Overview"

# version
#
_version_="2022.07.17"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-witness.sh"

# DEFAULT He miner hostname
#
host="controllinohotspot"

# json message keys to display in this order
#
keys="Total witnesses, Succesfully delivered"

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
url=http://$host/processlog

[ $DBG ] && echo "DBG.URL: $url"

# json response
#
json=$( wget $opts $url ); excode=$?

# {"status":200,
# "message":"\n\n\n\n
# General Witnesses Overview  \n----------------------------------\n
# Total witnesses                   =    25  (1.38/hour)\n
# Succesfully delivered             =    25   (100%)\n
# Failed                            =     0     (0%) \n"}
[ $DBG ] && echo "DBG.WGET.exitcode: $excode" && echo "DBG.JSON: $json" && echo "DBG.KEYS: $keys" && echo

# python code to process json
#
pycode=$( cat <<___
import sys,json
try: j = json.loads(r'$json')
except json.decoder.JSONDecodeError: sys.exit(-1)
result = {}
if j.get('status') != 200:
    print('status:', j.get('status'))
    print('message:', j.get('message'))
else:
    for line in j.get('message').split('\n'):
        if '$DBG': print('DBG.LINE:', line)
        if '=' not in line: continue
        key, val = line.split('=')
        key, val = key.strip(), val.strip().split()[0].strip()
        if '$DBG': print('DBG.RESULT:', key, '=>', val)
        result[key] = val
if '$DBG': print()
for key in '$keys'.split(', '):
    if '$DBG': print('DBG.KEY:', key, end=' ')
    print(result.get(key))
if '$DBG': print('DBG.UPTIME:', end=' ')
print('?')
if '$DBG': print('DBG.HOST:', end=' ')
print('$host')
___
)

# execute
#
$python -c "$pycode"
