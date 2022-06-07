#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from networkautomation.common.input_output_files import get_device_list_from_csv, write_info_to_csv, get_credentials
from networkautomation.common.main import run_command
from networkautomation.getconfigurations.main import get_stack_info
from networkautomation.global_variables import global_variables as gv

COMMAND = {
    "cisco_ios": ["show version"],
    "cisco_nxos": ["show version"],
    "alcatel_aos": ["show chassis", "show system"],
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

        command_list = COMMAND["{}_{}".format(vendor, platform)]
        device_information = {
            "vendor": vendor,
            "model": None, 
            "serial_number": None,
            "platform": platform, 
            "version": None, 
            "hostname": None,
            "ip_address": ip_address,
            "mac_address": None,
            "system_uptime": None,
        }
        for command in command_list:

            try:
                hostname = None
                hostname, command_output = run_command(vendor, platform, ip_address, username, password, enable_secret, command, True)

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

            device_information.update(command_output[0])
            device_information["hostname"] = hostname

            script_report.append({
                "Vendor": vendor,
                "Platform": platform,
                "IP Address": ip_address,
                "Command Issued": command,
                "Status": "Done",
                "Comments": ""
            })
        
        if hostname:
            for device_info_aux in get_stack_info(device_information):
                device_list_info.append(device_info_aux.copy())

    if device_list_info:
        output_filename = "Device Information"
        write_info_to_csv(None, output_filename, device_list_info)

    return script_report
