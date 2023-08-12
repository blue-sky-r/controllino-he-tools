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
_version_="2023.08.12"

# github
#
_github_="https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-witness-sel-unsel.sh"

# hotspot id (aplhanum string)
#
#hid=112A7iiPUF6cKCRGE4CT646LkQJ5gUmU51HsFYqtW5914fN9pMub
hid=<hotspot-id-string>

# retrieve all witnessing within range the lastN-hours (valid values 2H, 8H, 12H, 24H, 7D)
#
range=2H

# retrieve only activities (comma separated list, valid keys are Witness Beacon IOT+Data IOT+Rewards)
activities=Witness

# wget options
#
opts="--retry-on-host-error --retry-connrefused --retry-on-http-error=503 --timeout=7 --tries=3 -q -O -"

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

# explorer URL
#
url="https://explorer.moken.io/hotspots/$hid/activity?activityRange=$range&selectedActivities=$activities"

[ $DBG ] && echo "DBG.URL: $url"

# get selected and unselected witnessing
# wget -O - "https://explorer.moken.io/hotspots/112A7iiPUF6cKCRGE4CT646LkQJ5gUmU51HsFYqtW5914fN9pMub/activity?activityRange=8H&selectedActivities=Witness" | grep -o "\(Uns\|S\)elected"
witnessing=$( wget $opts "$url" | grep -o '\(Uns\|S\)elected' ); excode=$?

[ $DBG ] && echo "DBG.WGET.exitcode: $excode" && echo "DBG.witnessing: "$witnessing && echo

# Selected
[ $DBG ] && echo -n "DBG.selected: "
echo "$witnessing" | grep -c Selected

# Unselected
[ $DBG ] && echo -n "DBG.unselected: "
echo "$witnessing" | grep -c Unselected

# uptime
[ $DBG ] && echo -n "DBG.uptime: "
echo "?"

# host
[ $DBG ] && echo -n "DBG.host: "
echo "He-miner"
