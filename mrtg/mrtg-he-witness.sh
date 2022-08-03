#!/bin/bash

# For CONTROLLINO miner only - https://hotspot.controllino.com/
#  firmware_version: raspbian bionic 2022.07.14.0 - 2022.08.02 + dashboard 1.3.7 - 1.3.9

# about
#
_about_="mrtg probe to graph He miner General Witnesses Overview"

# version
#
_version_="2022.08.83"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-witness.sh"

# DEFAULT He miner hostname
#
host="controllinohotspot"

# key eval expressions to display in this order (use '_' instead of space in var names)
#
keys="Succesfully_delivered, Total_witnesses"

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

# {"data":{
#   "type":"process",
#   "attributes":
#       {"process":"\n\n\n\n
#       General Witnesses Overview  \n
#       ----------------------------------\n
#       Total witnesses                   =   123  (0.91/hour)\n
#       Succesfully delivered             =   122 (99.19%)\n
#       Failed                            =     1  (0.81%)
#       \n"}}}
[ $DBG ] && echo "DBG.WGET.exitcode: $excode" && echo "DBG.JSON: $json" && echo "DBG.KEYS: $keys" && echo

# python code to process json
#
pycode=$( cat <<___
import sys,json
try: j = json.loads(r'$json')
except json.decoder.JSONDecodeError: sys.exit(-1)
vars = {}
txt = j.get('data',{}).get('attributes',{}).get('process')
if not txt:
    print('json:', j)
    print('data:', j.get('data'))
else:
    for line in txt.split('\n'):
        if '$DBG': print('DBG.LINE:', line)
        if '=' not in line: continue
        key, val = line.split('=')
        key, val = key.strip().replace(' ', '_'), val.strip().split()[0].strip()
        if '$DBG': print('DBG.RESULT:', key, '=>', val)
        vars[key] = int(val)
if '$DBG': print()
for expr in '$keys'.split(', '):
    if '$DBG': print('DBG.EXPR:', expr, end=' = ')
    v = eval(expr, vars)
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
