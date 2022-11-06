# -*- coding: UTF-8 -*-

import json
import os
import sys

from classes import Client
from classes import Commands


def raise_exception(exception): sys.exit("[!] {}".format(exception))


if __name__ == '__main__':

    with open(os.path.join(os.path.dirname(__file__), './get_configs.txt'), 'r', encoding='utf-8') as file:     

        info = []
        line = file.readline()
        while line != '':

            if 'Root Directory:' in line:
                next_line = file.readline()
                root_dir = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Root directory not specified')

            elif 'Client Name:' in line:
                next_line = file.readline()
                client_name = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Client name not specified')
            
            elif 'Keepass Database:' in line:
                next_line = file.readline()
                keepass_db = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 and '.kdbx' in next_line else raise_exception('Keepass database not specified')
                # keepass_pwd = input("[>] Keepass password: ")
                keepass_pwd = 'HOX265huq!'
                
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                info.append(info_requested)
            
            line = file.readline()

    with open(f"{os.path.dirname(__file__)}/commands.json", 'r', encoding='utf-8') as commands: command_list = json.load(commands)

    client = Client(root_dir, client_name, keepass_db=keepass_db, keepass_pwd=keepass_pwd)
    for device in client.device_list:
        for info, command in command_list.items():          
            command = Commands(device, info, command[device.vendor_os])
            device.command_list.append(command)

    client.run()
    client.generate_report()
