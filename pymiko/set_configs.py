# -*- coding: UTF-8 -*-

import json
import os
import sys
import time

from classes import Client
from classes import Commands


def raise_exception(exception): sys.exit("[!] {}".format(exception))


if __name__ == '__main__':

    st = time.time()

    with open(os.path.join(os.path.dirname(__file__), './set_configs.txt'), 'r', encoding='utf-8') as file:     

        set_configs_info = []
        line = file.readline()
        while line != '':

            if 'Root Directory:' in line:
                next_line = file.readline()
                root_dir = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Root directory not specified')

            elif 'Client Name:' in line:
                next_line = file.readline()
                client_name = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Client name not specified')
                           
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip().replace(" ", "_").lower()
                set_configs_info.append(info_requested)
            
            line = file.readline()

    client = Client(root_dir, client_name)
    for info in get_configs_info:
        break
    
    client.generate_config()

    print('Execution time:', time.time() - st, 'seconds')
