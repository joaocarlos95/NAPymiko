# -*- coding: UTF-8 -*-

import json
import os
import re
import sys
import time

from classes import Client
from classes import Command
from classes import Upgrade


def raise_exception(exception): sys.exit("[!] {}".format(exception))


if __name__ == '__main__':

    st = time.time()

    with open(os.path.join(os.path.dirname(__file__), './upgrade.txt'), 'r', encoding='utf-8') as file:     

        get_configs_info = ['Device Information', 'File System']
        upgrade_steps_info = []
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
                keepass_pwd = 'HOX265huq#'
            
            elif 'FTP Server' in line:
                next_line = file.readline()
                ftp_server = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Root directory not specified')

            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                upgrade_steps_info.append(info_requested)
            
            line = file.readline()

    client = Client(root_dir, client_name, keepass_db=keepass_db, keepass_pwd=keepass_pwd, ftp_server=ftp_server)
    for device in client.device_list:
        device.get_configs(get_configs_info)
        device.run_upgrade(upgrade_steps_info)
        device.disconnect()

    # print('Execution time:', time.time() - st, 'seconds')
