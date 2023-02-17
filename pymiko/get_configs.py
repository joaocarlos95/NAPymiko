# -*- coding: UTF-8 -*-

import json
import os
import pprint
import sys
import time

from classes import Client
from multiprocessing import Manager, Process


def raise_exception(exception): sys.exit("[!] {}".format(exception))


if __name__ == '__main__':

    st = time.time()

    with open(os.path.join(os.path.dirname(__file__), './get_configs.txt'), 'r', encoding='utf-8') as file:     

        get_configs_info = []
        line = file.readline()
        while line != '':

            if 'Root Directory:' in line:
                next_line = file.readline()
                root_dir = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Root directory not specified')

            elif 'Client Name:' in line:
                next_line = file.readline()
                client_name = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 else raise_exception('Client name not specified')
            
            elif 'Keepass Database:' in line:
                # IF NO KEEPASS DATABASE IS SPECIFIED, AN EXCEPTION IS RAISED AND SHOULDN'T. MUST PASS AND IF CANNOT FIND CREDENTIALS, THEN AN EXCEPTION MUST BE RAISED
                next_line = file.readline()
                keepass_db = next_line.split('>')[1].strip() if '>' in next_line and len(set(next_line)) > 2 and '.kdbx' in next_line else raise_exception('Keepass database not specified')
                # keepass_pwd = input("[>] Keepass password: ")
                keepass_pwd = 'HOX265huq#'
                
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                get_configs_info.append(info_requested)
            
            line = file.readline()

    client = Client(root_dir, client_name, keepass_db=keepass_db, keepass_pwd=keepass_pwd)
    manager = Manager()
    report = manager.list()

    process_list = []
    for devive in client.device_list:
        # Append in a list the process of acquiring information for the device
        process = Process(target=devive.run_get_configs, args=(get_configs_info, report))
        process_list.append(process)

    # Initiate the process of acquiring configurations for each device
    for process in process_list:
        process.start()
    # Wait for each process to finish
    for process in process_list:
        process.join()

    # Generage reports for this script
    client.report = report
    client.generate_config_report()
    client.generate_config_parsed()

    # Save all script output in a json file
    with open(f"{client.dir}/outputfiles/script_output.json", "w") as outfile:
        outfile.write(json.dumps(list(report), indent=2))

    if 'Network Diagram' in get_configs_info:
        client.generate_diagram()

    print('Execution time:', time.time() - st, 'seconds')
