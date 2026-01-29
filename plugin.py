"""
<plugin key="SNMPReaderMK" name="SNMP Reader by MK v1.0beta" author="Marcin Kapski" version="1.0">
    <description>
        <h2>SNMP Python - CHATGPT</h2>
        Panel konfiguracji urządzeń SNMP
	Format danych: ID,NAME,OID,INTERVAL,DIVIDED   nie usuwaj wpisów, najpierw usuń DEVICES a potem zmieniaj konfiguracje
    </description>
    <params>
        <param field="Address" label="IP urządzenia" width="150px" default="192.168.1.100"/>
	<param field="Port" label="Port" default="161"/>
        <param field="Mode1" label="Community SNMP" width="150px" default="public"/>
        <param field="Mode2" label="Konfiguracja czujek (ID,Nazwa,OID,INTERVAL)" cols="40" rows="10" witdth="200px" default=""/>
        <param field="Mode3" label="Debug" width="150px">
            <options>
                <option label="None" value="0" default="true"/>
                <option label="Debug" value="1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import subprocess
import Domoticz
import time
import os
import json

class SNMPPlugin:
    def __init__(self):
        self.devices_cfg = {}   # ID -> dict
        self.devices_cfg_prev = {}
        self.last_poll = {}     # ID -> timestamp
        self.debug = False
        self.log = False
        self.needDeviceSync = True;

    # --------------------------------------------------
    # START
    # --------------------------------------------------
    def onStart(self):
        Domoticz.Log("SNMP Plugin started - Author: Marcin Kapski, mkapski@gmail.com")

        # Debug
        dbg = Parameters.get("Mode3", "0")
        self.debug = (dbg == "1")
        if self.debug:
            Domoticz.Debugging(1)
            Domoticz.Debug("Debug enabled")

        self.parse_config()
        self.sync_devices()

    # --------------------------------------------------
    # PARSE CONFIG (Mode2 textarea)
    # --------------------------------------------------
    def parse_config(self):
        self.devices_cfg = {}
        Domoticz.Log("Parse_config Started...")

        cfg = Parameters.get("Mode2", "").strip()
        if not cfg:
            Domoticz.Log("No device configuration provided")
            return

        for line in cfg.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 6:
                Domoticz.Error(f"Invalid config line: {line}")
                continue

            dev_id, name, oid, interval, typ, divider = parts

            if not interval.isdigit():
                Domoticz.Error(f"Invalid interval for {dev_id}")
                continue
            if not dev_id.isdigit():
                Domoticz.Error(f"Invalid Dev_id for {dev_id}")
                continue

            self.devices_cfg[dev_id] = {
                "name": name,
                "oid": oid,
                "interval": int(interval),
                "typ": typ,
                "divider": int(divider)
            }

        Domoticz.Log(f"Parsed devices: {self.devices_cfg}")
        Domoticz.Log(f"Checking previous configuration (from file devices.json)")
        if os.path.exists("devices.json"):
            Domoticz.Log(f"Odczytuje z pliku...")
            with open("devices.json", "r") as f:
                self.devices_cfg_prev = json.load(f)
        else:
            Domoticz.Log(f"Zapisuję do pliku")
            self.devices_cfg_prev = {str(k): {"name": v["name"], "typ": v["typ"]}
                                     for k, v in self.devices_cfg.items()}
            with open("devices.json", "w") as f:
                json.dump(self.devices_cfg, f, indent=2)

    # --------------------------------------------------
    # CREATE / UPDATE DEVICES
    # --------------------------------------------------
    def sync_devices(self):
        count = len(Devices);
        if self.log:
            Domoticz.Log(f"Sync_devices count:{count}")
        updated = False
        for dev_id, cfg in self.devices_cfg.items():
            name = cfg.get("name", "")
            oid = cfg.get("oid", "")
            typ = cfg.get("typ", "")
            interval = cfg.get("interval", "")
            divider = cfg.get("divider","")
            # Logowanie wszystkich zmiennych
            Domoticz.Log(f"Sync device - dev_id: {dev_id}, name: {name}, oid: {oid}, interval: {interval}, divider: {divider}")

            if int(dev_id) not in Devices:
                Domoticz.Log(f"Creating device {dev_id}, {name}, {oid}, {interval}, {divider}")
                Domoticz.Device(Name=name, Unit=int(dev_id), TypeName=typ, Type=0, Subtype=0, Switchtype=0, Image=0, Used=1).Create()
            else:
                
                Domoticz.Log(f"Update need.. checking changes... ")
                to_update = False
                if int(dev_id) in self.devices_cfg_prev:
                    if self.devices_cfg_prev[dev_id]["name"] != self.devices_cfg[dev_id]["name"]:
                        to_update = True;
                    if self.devices_cfg_prev[dev_id]["typ"] != self.devices_cfg[dev_id]["typ"]:
                        to_update = True;
                    if to_update:
                        updated = True
                        d = Devices[int(dev_id)]
                        Domoticz.Log(f"Removing device, ReCreate device: Will be: {dev_id},{name},{typ} ")
                        d.Delete();
                        Domoticz.Device(Name=name, Unit=int(dev_id), TypeName=typ, Type=0, Subtype=0, Switchtype=0, Image=0, Used=1).Create()
                    else:
                        Domoticz.Log(f"Update not need {dev_id} ")
                else:
                   updated = True;
        if updated:
            Domoticz.Log(f"Zapisuję zaminy do pliku")
            #self.devices_cfg_prev = {str(k): {"name": v["name"], "typ": v["typ"]}
            #                         for k, v in self.devices_cfg.items()}
            with open("devices.json", "w") as f:
                json.dump(self.devices_cfg, f, indent=2)





    def read_snmp(self, host, oid, community="public"):
     try:
        if self.log:
            Domoticz.Log(f"Start reading IP SNMP.....")
        result = subprocess.run(
            [
                "snmpget",
                "-v2c",
                "-c", community,
                "-t", "1",    # timeout snmp (sek)
                "-r", "0",    # brak retry
                host,
                oid
            ],
            capture_output=True,
            text=True,
            timeout=1.5      # HARD timeout Pythona
        )

        if result.returncode != 0:
            raise Exception(result.stderr.strip())

        # wyciągamy tylko wartość po '='
        return result.stdout.split("=", 1)[1].strip()

     except subprocess.TimeoutExpired:
        Domoticz.Error("SNMP timeout")
     except Exception as e:
        Domoticz.Error(f"SNMP error: {e}")

     return None

    # --------------------------------------------------
    # HEARTBEAT (polling)
    # --------------------------------------------------
    def onHeartbeat(self):
        Domoticz.Log(f"HartBeat Started.")
        #if self.needDeviceSync and len(Devices) > 0:
        #    self.parse_config()
        #    self.sync_devices()
        #    self.needDeviceSync = False
        count = len(Devices);
        if self.log:
            Domoticz.Log(f" Heartbeat Devices count:{count}")
        now = time.time()
        host = Parameters["Address"]
        for dev_id, cfg in self.devices_cfg.items():
            if self.log:
                Domoticz.Log(f"HartBeat loop....")
            unit = int(dev_id)
            last = self.last_poll.get(unit, 0)
            set_interval =  cfg["interval"]
            calc_interval = now - last
            if self.log:
                Domoticz.Log(f"Device {unit}-{now}-{last}-{set_interval}-{calc_interval}")
            if now - last > set_interval:
                if self.log:
                    Domoticz.Log(f"SNMP Updating......")
                self.last_poll[unit] = now
                value = self.read_snmp(host, cfg["oid"])
                if value is None:
                    if self.log:
                        Domoticz.Log(f"SNMP read failed for device {unit}")
                    continue

                if unit in Devices:
                    value_str = str(value).strip()
                    num_str = value_str.split(":")[-1].strip()
                    nval = int(num_str)
                    if self.devices_cfg[dev_id]["divider"] != 1:
                        sval = nval / self.devices_cfg[dev_id]["divider"]
                    else:
                        sval = nval
                    Devices[unit].Update(nValue=int(nval), sValue=str(sval), Name = str(self.devices_cfg[dev_id]["name"]))
                    if self.log:
                        Domoticz.Log(f"SNMP end {unit}: {value} - {nval}")

# --------------------------------------------------
# GLOBAL
# --------------------------------------------------
_plugin = SNMPPlugin()

def onStart():
    _plugin.onStart()

def onHeartbeat():
    _plugin.onHeartbeat()
