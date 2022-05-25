# mrtg probes for controllinohotspot

[Controllino Hotspot](https://hotspot.controllino.com/) is [Raspberry Pi4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) 
based LoRaWAN gateway compatible with [Helium network](https://www.helium.com/).

### Objective

The main objective is to visualy display various [Controllino Hotspot](https://hotspot.controllino.com/) parameters in [mrtg](https://oss.oetiker.ch/mrtg/) grapher
to get quick feedback about health status of the miner. Due to frequent changes in [Helium network](https://www.helium.com/)
it is historical visual comparision the fast way to evaluate required action.

A few interesting facts about Your expensive controllino miner:

* controllino manufacturer has full access to and control of Your home LoRaWAN hotspot/miner

* You have only very limited access to controllino graphical GUI via web interface

* controllino does not support SNMP nor SSH shell access

* openning Your controllino will void Your warranty 

### Requirements

All mrtg probes are shell scripts:

* bash - script parameters and flow handling

* wget - access to controllino HTTP API

* python3 - for json handling


    All published scripts do not require remote ssh / snmp access and work 
    with unmodified / untouched original controllino hardware and software

### firmware updates

The implementation of all mrtg probes is utilizing existing very limited unofficial 
and undocumented controllino HTTP API

    Please note that implemented scripts are highly firmware version dependent and might 
    stop working on the next firmware update without any warning

### mrtg probes

Each probe script retrieves data via HTTP API request and formats selecteed values into mrtg
4-line format to be seamlessly processed by mrtg tool. You can find more details in any [mrtg doc](https://oss.oetiker.ch/mrtg/doc/mrtg-reference.en.html):

    External Monitoring Scripts

    If you want to monitor something which does not provide data via snmp you can use some external program to do the data gathering.
    The external command must return 4 lines of output:

    Line 1      current state of the first variable, normally 'incoming bytes count'
    Line 2      current state of the second variable, normally 'outgoing bytes count'
    Line 3      string (in any human readable format), telling the uptime of the target.
    Line 4      string, telling the name of the target.

    Depending on the type of data your script returns you might want to use the 'gauge' or 'absolute' arguments for the Options keyword.
 
Short usage help can be invoked by -h parameter. Detailed debug mode is available with -d parameter.

Here are some controllino probes to visualize various metrics in [mrtg](https://oss.oetiker.ch/mrtg/):

  * [HNT rewards](mrtg-he-rewards.sh) - mrtg probe to retrieve HNT rewards for time period
  
  * [RAM usage / CPU temperature](mrtg-he-ram-temp.sh) - mrtg probe to retrieve RAM utilization and CPU temperature

  * [blockchain height](mrtg-he-height.sh) - mrtg probe to retrieve blockchain height

#### mrtg - HNT Rewards 

Script [mrtg-he-rewards.sh](mrtg-he-rewards.sh) retrieves total and average HNT rewards
(defined by json keys variable in config section at the top of the script).

To get integer values for mrtg the HNT rewards are multiplied by 1000, so the script is actually
returning mili-HNT (mHNT), for  example 500 mHNT = 0.5 HNT. Therefore we have to properly
adujst following mrtg per target factor config options, see [mrtg doc](https://oss.oetiker.ch/mrtg/doc/mrtg-reference.en.html) for details:

    Factor[target]: 0.001
    YTicsFactor[target]: 0.001

Short usage help invoked by -h:

    mrtg$ ./mrtg-he-rewards.sh -h
    
    = mrtg probe to graph He miner rewards = ver 2022.05.15 =
    
    usage: ./mrtg-he-rewards.sh [-h] [-d] [host [days]]
    
    -h   ... show this usage help
    -d   ... additional debug info
    host ... host/miner to connect to (default controllinohotspot)
    days ... reward interval to query in days, valid values are 1,7,14 (default 1)
    
    https://github.com/blue-sky-r/controllino-he-tools/blob/main/mrtg/mrtg-he-rewards.sh

Example of mrtg weekly graph:

![screenshot](../screenshot/mrtg-rewards.jpg)


### Troubleshooting

What to do if something goes wrong or does not work:

* try debug / verbose mode - check usage help how to

* try using explicit parameters (not default ones)

* check the script source and try to increase timeouts, retries etc ...

##### keywords

shell bash python3 controllino controllinohotspot json he helium miner HNT mrtg probe monitoring

