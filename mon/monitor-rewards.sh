#!/bin/bash

# For CONTROLLINO miner only - https://hotspot.controllino.com/
#  firmware_version: raspbian bionic 2022.08.17.1 + dashboard 1.4.1
#  firmware_version: raspbian bionic 2022.10.28.0 + dashboard 1.4.2
#  firmware_version: raspbian bionic 2023.02.87.0 + dashboard 1.4.3
#
# > nohup monitor-rewards.sh '1h 23m' &

# about
#
_about_="HNT rewards monitor - restarts container on flat rewards"

# version
#
_version_="2023.03.12"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mon/mon-rewards.sh"

# json key to check
# {"total":0.31404812,"sum":31404812,"stddev":0.012765751345,"min":0,"median":0.01125426,"max":0,"avg":0.0125619248}}
jkey='total'

# syslog tag
#
tag="mon-rewards"
out="logger -t $tag"

# DEFAULT host
#
host="controllinohotspot"

# wget options
#
opts="--retry-on-host-error --retry-connrefused --retry-on-http-error=503 --timeout=20 --tries=5 -q -O -"

# python
#
python="python3 -c"

# usage help
#
[ $# -lt 1 -o "$1" == "-h" ] && cat <<< """
= $_about_ = ver $_version_ =

usage: $0 [-h] [-d] period [host]

-h     ... show this usage help
-d     ... output to stdout (default to syslog with tag $tag)
period ... how often to check (human friendly format like '1h 23m 45s')
host   ... host/miner to connect to (default $host)

$_github_
""" && exit 1

# optional debug
#
[ "$1" == "-d" ] && out=echo && shift

# period - how often to check
#
period=${1}

# He miner hostname
#
[ $2 ] && host=$2

# controllino urls
#
url_rewards=http://$host/rewards/1
url_restart=http://$host/miner-restart

# just log start
#
$out "START - pid: $$ - sleep: $period - host: $host"

# python code to process json from stdin
#
pycode=$( cat <<___
import sys,json
try: j = json.load(sys.stdin)
except json.decoder.JSONDecodeError: sys.exit(-1)
if j.get('status') == 200: print(j.get('rewards').get('$jkey'))
___
)

# get json response
json=$( wget $opts $url_rewards ); excode=$?

# {"status":200,"rewards":{"total":0.31404812,"sum":31404812,"stddev":0.012765751345,"min":0,"median":0.01125426,"max":0,"avg":0.0125619248}}
$out "INIT REWARDS WGET url: $url_rewards exitcode: $excode" && $out "JSON: $json"

# json python processing
rewards_last=$( echo "$json" | $python "$pycode" )
# show result to stderr and exit if rewards is empty string
[ -z "$rewards_last" ] && >&2 echo "ERROR getting rewards: $rewards_last from json: $json" && exit 2

# json returned in case of HTTP 503 error
json503='{"status":503}'

# limit tries in case of http 503
max_tries=10

# wait betwwen repeated attempts in case of http 503
sleep_tries='1m 23s'

# loop forever
while sleep $period
do
    # try to get rewards multiple times in case of 503
    for try in $(seq $max_tries)
    {
        # actual rewards
        json=$( wget $opts $url_rewards ); excode=$?
        # {"status":200,"rewards":{"total":0.31404812,"sum":31404812,"stddev":0.012765751345,"min":0,"median":0.01125426,"max":0,"avg":0.0125619248}}
        $out "REWARDS ${try} of ${max_tries}. try WGET url:$url_rewards exitcode: $excode" && $out "JSON: $json"
        # will retry only on http 503
        [ "$json" != "$json503" ] && break
        # sleep between retries
        sleep $sleep_tries
    }
    # returned json
    rewards=$( echo "$json" | $python "$pycode" )
    $out "REWARDS: $rewards_last -> $rewards"

    # loop if no rewards returned
	[ -z "$rewards" ] && continue

    # check if there is a change = ok
	[ "$rewards" != "$rewards_last" ] && rewards_last=$rewards && continue

	# restart container
	json=$( wget $opts $url_restart ); excode=$?
	# {"data":{"type":"container","attributes":{"name":"miner","state":"running"}}}
	$out "RESTART WGET url:$url_restart exitcode: $excode" && $out "JSON: $json"
done
