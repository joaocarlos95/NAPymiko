#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from networkautomation.common.input_output_files import get_device_list_from_csv, write_info_to_csv, get_credentials
from networkautomation.common.main import run_command
from networkautomation.global_variables import global_variables as gv

COMMAND = {
    "cisco_ios": ["show interfaces status", "show power inline", "show interfaces description", "show interfaces switchport"],
}


def init():

    device_list = get_device_list_from_csv(gv.get_device_list_pathname())
    
    script_report = []
    device_list_info = []
    for device_information in device_list:

        vendor = device_information["vendor"]
        platform = device_information["platform"]
        ip_address = device_information["ip_address"]
        enable_secret = device_information["enable_secret"]
        
        # Use Keepass credentials
        if gv.get_keepass_to_use():

            try:
                username, password = get_credentials(gv.get_keepass_pathname(), gv.get_client_name(), ip_address)

            except Exception as exception:
                print(exception)
                script_report.append({
                    "Vendor": vendor,
                    "Platform": platform,
                    "IP Address": ip_address,
                    "Command Issued": None,
                    "Status": "Ongoing",
                    "Comments": exception
                })
                continue
        # Use device_list file credentials
        else:
            username = device_information["username"]
            password = device_information["password"]
    
        if "{}_{}".format(vendor, platform) not in COMMAND.keys():
            continue
        command_list = COMMAND["{}_{}".format(vendor, platform)]
        
        interface_list = {}
        device_information = {
            "device_hostname": None,
            "device_ip": ip_address,
            "interface_name": None,
            "interface_status": None,
            "interface_speed": None,
            "interface_duplex": None,
            "interface_type": None,
            "switchport_mode": None,
            "vlan": None,
            "voice_vlan": "n/a",
            "native_vlan": "n/a",
            "poe_status": "n/a",
            "poe_power": "n/a",
            "poe_class": "n/a",
            "poe_max": "n/a",
            "interface_description": None,
        }
        for command in command_list:
            try:
                hostname, command_output = run_command(
                    vendor, platform, ip_address, username, password, enable_secret, command, True)

            except Exception as exception:
                print(exception)
                script_report.append({
                    "Vendor": vendor,
                    "Platform": platform,
                    "IP Address": ip_address,
                    "Command Issued": command,
                    "Status": "Ongoing",
                    "Comments": exception
                })
                continue

            device_information["device_hostname"] = hostname
            for interface_info in command_output:

                if "vlan" in interface_info.keys():
                    if interface_info["vlan"] == "routed":       
                        interface_info["interface_type"] = "routed"
                    else:
                        interface_info["interface_type"] = "switchport"
                
                elif "trunk_vlans" in interface_info.keys():
                    if "trunk" in interface_info["switchport_mode"]:
                        interface_info["voice_vlan"] = "n/a"
                        if interface_info["trunk_vlans"][0] == "ALL":
                            interface_info["vlan"] = "All"
                        else:
                            interface_info["vlan"] = interface_info["trunk_vlans"][0].replace(",", ", ")
                              
                    elif "access" in interface_info["switchport_mode"]:
                        interface_info["switchport_mode"] = "access"
                        interface_info.pop("native_vlan", None)
                        if interface_info["voice_vlan"] == "none":
                            interface_info["voice_vlan"] = None
                    
                    elif "down" in interface_info["switchport_mode"]:
                        if "trunk" in interface_info["switchport_admin_mode"]:
                            interface_info["switchport_mode"] = "trunk"
                            interface_info["voice_vlan"] = "n/a"
                            if interface_info["trunk_vlans"][0] == "ALL":
                                interface_info["vlan"] = "All"
                            else:
                                interface_info["vlan"] = interface_info["trunk_vlans"][0].replace(",", ", ")
                       
                        elif "access" in interface_info["switchport_admin_mode"]:
                            interface_info["switchport_mode"] = "access"
                            interface_info.pop("native_vlan", None)
                            if interface_info["voice_vlan"] == "none":
                                interface_info["voice_vlan"] = None

                        elif "dynamic" in interface_info["switchport_admin_mode"]:
                            interface_info["switchport_mode"] = "dynamic auto"
                            interface_info["vlan"] = None
                            interface_info["voice_vlan"] = None
                            interface_info["native_vlan"] = None

                    interface_info.pop("switchport_admin_mode", None)
                    interface_info.pop("trunk_vlans", None)
                    interface_info.pop("access_vlan", None)
                    
                if interface_info["interface_name"] not in interface_list:
                    interface_list[interface_info["interface_name"]] = device_information.copy()
                interface_list[interface_info["interface_name"]].update(interface_info)

            script_report.append({
                "Vendor": vendor,
                "Platform": platform,
                "IP Address": ip_address,
                "Command Issued": command,
                "Status": "Done",
                "Comments": ""
            })

        for key, value in list(interface_list.items()):
            if key.startswith("Vl"):
                del interface_list[key]
            elif value["interface_status"] == None:
                del interface_list[key]
        
        device_list_info.extend(list(interface_list.copy().values()))

    if device_list_info:
        output_filename = "Interfaces Information"
        write_info_to_csv(None, output_filename, device_list_info)

    return script_report