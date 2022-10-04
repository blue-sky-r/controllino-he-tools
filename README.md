# Controllino He miner tools

Here are some additional utilities I have implemented and been in active use on my home monitoring
rig running [alpine](https://www.alpinelinux.org/) linux (no systemd ;-). The scripts are mixture of bash and python
programming for quick and easy implementation and fixing producing the immediate results - high ROI. 
As the [Controllino Hotspot](https://hotspot.controllino.com/) firmware is still under heavy development 
the changes are frequent and there is no backward compatibility maintained or promised = use at your own risk:   

    Please note that these utilities are highly firmware version dependent and might 
    stop working on the next firmware update without any warning


### What is Controllino

[Controllino Hotspot](https://hotspot.controllino.com/) is [Raspberry Pi4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) 
based LoRaWAN gateway compatible with [Helium network](https://www.helium.com/) and works as a full [HNT](https://www.helium.com/token) crypto miner.

Controllino provides only graphical web interface, but no remote access like ssh or snmp for monitoring the running Raspbian OS.
To get the full access to Raspbian the physical access to controllino HW is required and SD card with Raspbian
has to be modified. Such jailbreak will unfortunately void the warranty and will probably be lost
on the next sw remote upgrade. 

    All published scripts do not require remote ssh / snmp access and work 
    with unmodified / untouched original controllino hardware and software

### Utilities  

Here are some additional utilities I have implemented and been happily using:

* [log viewers](log/) - to retrieve live log entries (console.log, error.log) remotely:

  * [ws_read](log/ws_read.py) - read via websocket ws:// (just proof-of-concept, use ws_tail)
  
  * [ws_tail](log/ws_tail.py) - websocket tail for console log

  * [ws_classify](log/ws_classify.py) - console log classifier, outputs stats on signal

* [mrtg probes](mrtg/) - to visualize various metrics in famous snmp based [mrtg](https://oss.oetiker.ch/mrtg/) grapher:

  * [HNT rewards](mrtg/mrtg-he-rewards.sh) - mrtg probe to retrieve HNT rewards for time period
  
  * [RAM usage / CPU temperature](mrtg/mrtg-he-ram-temp.sh) - mrtg probe to retrieve RAM utilization and CPU temperature

  * [blockchain height](mrtg/mrtg-he-height.sh) - mrtg probe to retrieve blockchain height - deprecated since fw 1.3.9 (light hotspots)

  * [witnesses overview](mrtg/mrtg-he-witness.sh) - mrtg probe to retrieve General Witnesses statistics   

### Troubleshooting

What to do if something goes wrong or does not work:

* try debug / verbose mode - check usage help how to

* try using explicit parameters (not default ones)

* check the script source and try to increase timeouts, retries etc ...

##### keywords

shell bash python3 websock console.log error.log controllino he helium miner HNT mrtg probe monitoring

