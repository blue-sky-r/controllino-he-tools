# R.I.P. Controllino

    Update 03/2023 - Controllino firmware has been discontinued and replaced by very limited 
    Nebra firmware which doesn't provide any miner operational details nor logs. So from this date
    all tools published here become unusable and You have to pay for Nebra Diagnostic.
    
[Nebra Ltd providing updates for Controllino/Conelcom Hotspots](https://www.nebra.com/blogs/news/nebra-ltd-providing-updates-for-controllino-conelcom-hotspots)

# controllinohotspot remote monitors

[Controllino Hotspot](https://hotspot.controllino.com/) is [Raspberry Pi4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) 
based LoRaWAN gateway compatible with [Helium network](https://www.helium.com/).

### Monitors  

Here are some additional monitors to help if miner is not doing witnessing/beaconing:

* [monitor_rewards](monitor_rewards.sh) - monitor rewards and restart if rewards are flatlined
  
### Objective

The main objective is to remotely restart miner in case of any suspicious behaviour.
 
### Requirements

All mrtg monitors are shell scripts using:

* bash - script parameters and flow handling

* wget - access to controllino HTTP API

    All published scripts do not require remote ssh / snmp access and work 
    with unmodified / untouched original controllino hardware and software

### firmware updates warning

The implementation of all mrtg probes is utilizing existing very limited unofficial 
and undocumented controllino HTTP API

    Please note that implemented scripts are highly firmware version dependent and might 
    stop working on the next firmware update without any warning

### Troubleshooting

What to do if something goes wrong or does not work:

* check the syslog

* try debug / verbose mode - check usage help how to

* try using explicit parameters (not default ones)

* check the script source and try to increase timeouts, retries etc ...

##### keywords

shell bash controllino controllinohotspot he helium miner HNT monitoring
