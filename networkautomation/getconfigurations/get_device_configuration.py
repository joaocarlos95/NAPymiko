#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from networkautomation.common.input_output_files import get_device_list_from_csv, write_info_to_txt, get_credentials
from networkautomation.common.main import run_command
from networkautomation.global_variables import global_variables as gv

COMMAND = {
    "cisco_ios": "show running-config",
    "cisco_nxos": "show running-config",
    "alcatel_aos": "show configuration snapshot",
    "cisco_wlc": "show run-config",
}


def init():

    device_list = get_device_list_from_csv(gv.get_device_list_pathname())

    gv.set_raw_output(False)

    script_report = []
    for device_information in device_list:

        vendor = device_information["vendor"]
        platform = device_information["platform"]
        ip_address = device_information["ip_address"]
        enable_secret = device_information["enable_secret"]
        command = COMMAND["{}_{}".format(vendor, platform)]
        
        try:
            # Use Keepass credentials
            if gv.get_keepass_to_use():
                username, password = get_credentials(gv.get_keepass_pathname(), gv.get_client_name(), ip_address)
            # Use device_list file credentials
            else:
                username = device_information["username"]
                password = device_information["password"]
            
            hostname, command_output = run_command(vendor, platform, ip_address, username, password, enable_secret, command, False)

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

        output_filename = "Device Configuration - {} ({})".format(hostname, ip_address)
        write_info_to_txt(None, output_filename, command_output)

        script_report.append({
            "Vendor": vendor,
            "Platform": platform,
            "IP Address": ip_address,
            "Command Issued": command,
            "Status": "Done",
            "Comments": ""
        })

    gv.set_raw_output(True)
    
    return script_report
