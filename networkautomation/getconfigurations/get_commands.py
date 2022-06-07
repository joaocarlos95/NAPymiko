#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from networkautomation.common.input_output_files import get_device_list_from_csv, get_credentials, write_info_to_txt
from networkautomation.common.main import run_command
from networkautomation.global_variables import global_variables as gv


def init():

    device_list = get_device_list_from_csv(gv.get_device_list_pathname())
    
    script_report = []
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
                #print(exception)
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
        
        device_commands_output = ""
        with open(gv.get_command_list_pathname(), "r") as command_list:
            for line in command_list:
                command = line.rstrip()
       
                try:
                    hostname, command_output = run_command(
                        vendor, platform, ip_address, username, password, enable_secret, command, False)

                except Exception as exception:
                    #print(exception)
                    script_report.append({
                        "Vendor": vendor,
                        "Platform": platform,
                        "IP Address": ip_address,
                        "Command Issued": command,
                        "Status": "Ongoing",
                        "Comments": exception
                    })
                    continue

                device_commands_output += command_output

                script_report.append({
                    "Vendor": vendor,
                    "Platform": platform,
                    "IP Address": ip_address,
                    "Command Issued": command,
                    "Status": "Done",
                    "Comments": ""
                })
        
        output_filename = "Custom Commands - {} ({})".format(hostname, ip_address)
        write_info_to_txt(None, output_filename, device_commands_output)
        
    return script_report