#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import json
import re
import sys, os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from classes import Device
from concurrent.futures import ProcessPoolExecutor, wait

DEVICE_LIST = "C:/Users/joao.costa/OneDrive - Warpcom Services S.A/Warpcom/01. Clientes/Vieira de Almeida/04. Automation/inputfiles/device_list.csv"
UPGRADE_LIST = "C:/Users/joao.costa/OneDrive - Warpcom Services S.A/Warpcom/01. Clientes/Vieira de Almeida/04. Automation/inputfiles/upgrade.json"
BASE_DIR = "C:/Users/joao.costa/OneDrive - Warpcom Services S.A/Warpcom/03. File Server/02. Switches"

MAX_THREADS = 8

def main(device):

        device = Device(device['platform'], device['ip_address'], device['username'], device['password'], enable_secret="cisco@vda")
        device.ssh_connect()

        show_version = device.run_command('show version', textfsm=True)[0]
        show_file_systems = device.run_command('show file systems', textfsm=True)

        for switch_model in show_version['hardware']:
            index = show_version['hardware'].index(switch_model)
            
            image_target_version = ios_list[show_version['hardware'][index]]['target_version']
            image_filename = ios_list[show_version['hardware'][index]]['image']
            image_space = ios_list[show_version['hardware'][index]]['space']
            image_md5 = ios_list[show_version['hardware'][index]]['md5']

            # Add all used flash memories to a dict[free_space]
            flash_list = {}
            for flash in show_file_systems.split('\n'):
                flash_disk = re.search('flash:|flash-\d:|flash\d:', flash)
                if flash_disk: flash_list[flash_disk.group()] = flash.split()[2]

            for flash, flash_free_space in flash_list.items():
                # Verify space on disk
                # Enable scp server on switch and transfer new image
                if f"{image_filename}" not in device.run_command('dir'):              
                    if not flash_has_space(flash_free_space, image_space):
                        current_image = device.run_command('show boot', textfsm=True)[0]['boot_path'].split(f"{flash}")[1]
                        for dir_files in device.run_command('dir', textfsm=True):
                            # Delete older images
                            if current_image != dir_files['name'] and '.bin' in dir_files['name']:
                                device.delete_file(dir_files['name'], file_system=flash)

                    device.run_command('ip scp server enable', config_mode=True)
                    device.transfer_file(f"{BASE_DIR}/", flash, image_filename, image_filename)

                else:
                    print(f"[!] File already exists: {flash}{image_filename}")

            #flash = list(filter(re.compile('\D+\:').match, flash_list.keys()))[0]
            #device.upgrade(image_filename, file_system=flash)


def get_list_from_csv(pathname):
    ''' Get list from a csv file
    Parameters: csv filename
    Return: list of dictionaries '''

    with open(pathname, mode='r', encoding='utf-8') as file:
        
        list = []
        for row in csv.DictReader(file, skipinitialspace=True):
            if row['platform'].startswith('#'): pass
            else: list.append(row)
  
    return list


def flash_has_space(flash_free_space, image_space):

    if int(flash_free_space) - int(image_space) <= 0: return False
    else: return True


if __name__ == "__main__":

    device_list = get_list_from_csv(DEVICE_LIST)
    ios_list = json.loads(open(UPGRADE_LIST).read())

    pool = ProcessPoolExecutor(MAX_THREADS)
    FUTURE_LIST = []

    for device in device_list:
        print(device)
        FUTURE = pool.submit(main, device)
        FUTURE_LIST.append(FUTURE)

    wait(FUTURE_LIST)
