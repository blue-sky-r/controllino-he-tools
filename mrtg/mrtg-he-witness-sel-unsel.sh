#!/bin/bash

#  monitor witnessing activity for controllino with nebra firmware via
#  firmware_version: v1.0.2-14 (f97cd6b)

# ==================================================
# You have to edit entries in square brackets <text>
# ==================================================

# about
#
_about_="He selected and unselected witnessing"

# version
#
_version_="2023.08.15"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-witness-sel-unsel.sh"

# hotspot id (aplhanum string, not animal name)
#
#hid=112A7iiPUF6cKCRGE4CT646LkQJ5gUmU51HsFYqtW5914fN9pMub
hid=<hotspot-id-string>

# retrieve all witnessing within range the lastN-hours (valid values 2H, 8H, 12H, 24H, 7D)
#
range=2H

# retrieve only activities (comma separated list, valid keys are Witness Beacon IOT+Data IOT+Rewards)
#
activities=Witness

# count keys
#
key1=Selected
key2=Unselected

# local cache dir
#
cachedir=/tmp

# local cache lifetime
#
cachettl='65 mins'

# wget options
#
opts="--retry-on-host-error --retry-connrefused --retry-on-http-error=503 --timeout=7 --tries=3 -N"

# usage help
#
[ "$1" == "-h" ] && cat <<< """
= $_about_ = ver $_version_ =

usage: $0 [-h] [-d] [hid [range]]

-h    ... show this usage help
-d    ... additional debug info
hid   ... hotspot id (default $hid)
range ... witnessing in the last N-hours interval, valid values are 2H, 8H, 12H, 24H, 7D (default $range)

$_github_
""" && exit 1

# optional debug
#
[ "$1" == "-d" ] && DBG=1 && shift

# optional He miner hostname
#
[ $1 ] && hid=$1

# optional rewards period
#
[ $2 ] && range=$2

# use activities and range
#
[ $DBG ] && echo "DBG.explorer activities: $activities range: $range"

# explorer URL
#
#url="https://explorer.moken.io/hotspots/$hid/activity?activityRange=$range&selectedActivities=$activities&selectedLayer=hotspot"
#url="https://explorer.moken.io/hotspots/$hid/activity?activityRange=$range&selectedActivities=$activities"
page="activity?activityRange=$range&selectedActivities=$activities"
url="https://explorer.moken.io/hotspots/$hid/$page"
#
[ $DBG ] && echo "DBG.URL: $url"

# cache timestamp
#
cachets=0; [ -s "$cachedir/$page" ] && cachets=$(date -r "$cachedir/$page" +%s)

# cache expiration timestamp
#
expts=$(date -d "now - $cachettl" +%s)
#
[ $DBG ] && echo "DBG.CACHE file: $cachedir/$page  has timestamp: $cachets expiry $cachettl is timestamp: $expts or lower"

# cache empty or expired - update cache
#
if [ ! -f "$cachedir/$page" -o ! -s "$cachedir/$page" -o $cachets -lt $expts ]
then
	[   $DBG ] && echo "DBB.wget updating cache"
	[ ! $DBG ] && opts="$opts -q"
	wget $opts -P "$cachedir" "$url"
fi
#
[ $DBG ] && echo "DBG.CACHE: "$(ls -l $cachedir/$page)

# get selected and unselected witnessing
# wget -O - "https://explorer.moken.io/hotspots/112A7iiPUF6cKCRGE4CT646LkQJ5gUmU51HsFYqtW5914fN9pMub/activity?activityRange=8H&selectedActivities=Witness" | grep -o "\(Uns\|S\)elected"
witnessing=$( grep -o '\('$key1'\)\|\('$key2'\)' "$cachedir/$page" )
#
[ $DBG ] && echo "DBG.witnessing: "$witnessing && echo

# Selected
[ $DBG ] && echo -n "DBG.$key1: "
echo "$witnessing" | grep -c $key1

# Unselected
[ $DBG ] && echo -n "DBG.$key2: "
echo "$witnessing" | grep -c $key2

# uptime
[ $DBG ] && echo -n "DBG.uptime: "
echo "?"

# host
[ $DBG ] && echo -n "DBG.host: "
echo "controllino"
