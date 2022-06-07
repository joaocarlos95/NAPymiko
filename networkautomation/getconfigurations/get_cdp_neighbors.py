#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from networkautomation.common.input_output_files import get_device_list_from_csv, write_info_to_csv, get_credentials
from networkautomation.common.main import run_command
from networkautomation.global_variables import global_variables as gv

COMMAND = {
    "cisco_ios": "show cdp neighbors detail",
    "cisco_nxos": "show cdp neighbors detail",
    "cisco_wlc": "show cdp neighbors detail",
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
        command = COMMAND["{}_{}".format(vendor, platform)]
        
        device_information = {
            "local_hostname": None,
            "local_ip": ip_address,
            "neighbor_hostname": None,
            "neighbor_ip": None,
            "neighbor_model": None,
            "neighbor_interface": None,
            "local_interface": None,
        }

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

        device_information["local_hostname"] = hostname
        for neighbor_information in command_output:
            device_information.update(neighbor_information)
            device_list_info.append(device_information.copy())
        
        script_report.append({
            "Vendor": vendor,
            "Platform": platform,
            "IP Address": ip_address,
            "Command Issued": command,
            "Status": "Done",
            "Comments": ""
        })

    output_filename = "Neighbors (CDP)"
    write_info_to_csv(None, output_filename, device_list_info)

    return script_report