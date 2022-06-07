#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import os
import serial.tools.list_ports
import sys
from datetime import date
from pykeepass import PyKeePass

from networkautomation.global_variables import global_variables as gv



def get_serial_port():

    ports = serial.tools.list_ports.comports()
    for port, description, _ in sorted(ports):
        if "USB-to-Serial Comm Port" in description: return port
    raise Exception("[!] Serial port not identified")


def get_device_list_from_csv(pathname):
    ''' Get the IP address and credencials from every device in a csv file
    Parameters: csv filename
    Return: list of dictionaries '''

    with open(pathname, mode="r", encoding="utf-8") as file:
        
        device_list = []
        for row in csv.DictReader(file, skipinitialspace=True):
            if row["vendor"].startswith("#"): pass
            else: device_list.append(row)
  
    return device_list


def write_info_to_csv(extension_pathname, filename, device_list_info):
    ''' Write all devices information into a csv file 
    Parameters: filename, csv header, devices info '''

    pathname = gv.get_output_directory()
    if extension_pathname != None:
        pathname = "{}/{}".format(pathname, extension_pathname)
    os.makedirs(pathname, exist_ok = True)

    current_datetime = date.today().strftime("%Y%m%d")
    filename = "[{}] {}.csv".format(current_datetime, filename)
    
    print("[>] Writing information to the following file: {}".format(filename))
    with open("{}/{}".format(pathname, filename), 'w', newline='', encoding="utf-8") as file:  
        dict_writer = csv.DictWriter(file, device_list_info[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(device_list_info)


def generate_script_report(filename, device_list_error):
   
    device_list = get_device_list_from_csv(filename)
    for device in device_list:
        if device["ip_address"] in device_list_error.keys():
            device["Status"] = "Ongoing"
            device["Comments"] = device_list_error[device["ip_address"]]["exception"]
        else:
            device["Status"] = "Done"
            device["Comments"] = ""
        del device["username"]
        del device["password"]
    
    write_info_to_csv("../..", "{} - Script Result".format(gv.get_device_list_pathname()), device_list)

    return


def write_info_to_txt(extension_pathname, filename, device_info):
    ''' Write device information into a txt file 
    Parameters: filename, device info '''

    pathname = gv.get_output_directory()
    if extension_pathname != None:
        pathname = "{}/{}".format(pathname, extension_pathname)
    os.makedirs(pathname, exist_ok = True)

    current_datetime = date.today().strftime("%Y%m%d")

    # Characters that cannot be in the filename
    filename = filename.replace("|", "!")
    filename = filename.replace("/", "%")
    invalid_chars = '<>:"/\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "")

    filename = "[{}] {}.txt".format(current_datetime, filename)

    print("[>] Writing information to the following file: {}".format(filename))
    with open("{}/{}".format(pathname, filename), 'w', encoding="utf-8") as file:
        file.write(device_info)


def get_credentials(database, client, ip_address):
   
    try:
        keepass = PyKeePass(database, password=gv.keepass_db["password"])

    except Exception as exception:
        if "No such file or directory:" in str(exception):
            raise Exception("[!] Error getting keepass database")
        elif len(str(exception)) == 0:
            raise Exception("[!] Wrong keepass password")
        else:
            raise Exception("[!] Error (get_credentials function)]", exception)

    group = keepass.find_groups(name=client, first=True)
    if not group:
        raise Exception("[!] Group {} doesn't exist".format(client))
    
    # ADICIONADO "Telnet" ÀS TAGS DA PRÓXIMA LINHA
    entry = keepass.find_entries(group=group, url=ip_address, tags=["SSH", "Telnet"], recursive=True, first=True)
    if not entry:
        entry = keepass.find_entries(group=group, title="[Common]", notes="Central Authentication", first=True)
        if not entry:
            entry = keepass.find_entries(group=group, title="[Common]", notes="Local Authentication", first=True)
            if not entry:
                raise Exception("[!] Device with IP {} doesn't exist, neither common credencials".format(ip_address))

    username = entry.username
    password = entry.password

    return username, password

def raise_exception(exception): sys.exit("[!] {}".format(exception))

def get_set_configs_information(file):

    while True:
        line = file.readline()

        if "Root Directory:" in line:
            next_line = file.readline()
            root_directory = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 else raise_exception("Root directory not specified")
            gv.set_root_directory(root_directory)

        if "Client Name:" in line:
            next_line = file.readline()
            client_name = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 else raise_exception("Client name not specified")
            gv.set_client(client_name)

        elif "Device List:" in line:
            next_line = file.readline()
            device_list = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 else raise_exception("Device list not specified")
            gv.set_device_list(device_list)

        elif "Keepass Folder:" in line:
            next_line = file.readline()
            keepass_folder = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 else raise_exception("Keepass directory not specified")
            gv.set_keepass_directory(keepass_folder)
            
        elif "Keepass Database:" in line:
            next_line = file.readline()
            keepass_db = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 and ".kdbx" in next_line else raise_exception("Keepass database not specified")
            #password = input("[>] Keepass password: ")
            password = "HOX265huq!"
            gv.set_keepass_filename(keepass_db, password)
                
        elif "Custom Commands:" in line:
            next_line = file.readline()
            command_list = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 and ".txt" in next_line else raise_exception("Custom command list not specified")
            gv.set_command_list(command_list)

        elif "Connection Method:" in line:
            next_line = file.readline()
            connection_method = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 else raise_exception("Connection Method not specified")
            gv.set_connection_method(connection_method)
        
        elif "Custom Configuration:" in line:
            next_line = file.readline()
            configuration_file = next_line.split(">")[1].strip() if ">" in next_line and len(set(next_line)) > 2 else raise_exception("Connection Method not specified")
            gv.set_configuration_filename(configuration_file)
        
        elif "INFORMATION TO BE COLLECTED" in line or not line:
            return file