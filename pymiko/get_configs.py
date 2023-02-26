# -*- coding: UTF-8 -*-

import json
import os
import sys
import time
from multiprocessing import Manager, Process
from classes import Client
from getpass import getpass


def raise_exception(exception):
    sys.exit(f"[!] {exception}")


if __name__ == '__main__':
    st = time.time()

    with open(f"{os.path.dirname(__file__)}/json_files/commands.json", 'r', encoding='utf-8') as cmds:
        command_list = json.load(cmds)

    with open(os.path.join(os.path.dirname(__file__), './get_configs.txt'), 'r', encoding='utf-8') as file:     
        get_configs_info = []
        keepass_db = keepass_pwd = None

        for line in file:
            if 'Root Directory:' in line:
                line = file.readline()
                root_dir = line.split('>')[1].strip() if '>' in line and len(set(line)) > 2 else raise_exception('Root directory not specified')
            elif 'Client Name:' in line:
                line = file.readline()
                client_name = line.split('>')[1].strip() if '>' in line and len(set(line)) > 2 else raise_exception('Client name not specified')
            elif 'Keepass Database:' in line:
                line = file.readline()
                if '>' in line and len(set(line)) > 2 and '.kdbx' in line:
                    keepass_db = line.split('>')[1].strip()
                    keepass_pwd = getpass('[>] Keepass password: ')
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                get_configs_info.append(info_requested)
                if info_requested == 'Interfaces Counters':
                    while True:
                        try:
                            to_clear = {'true':True,'false':False}[input('[>] Clear counters (True or False)? ').lower()]
                            command_list['Interfaces Counters']['clear_counters']['to_clear'] = to_clear
                            break
                        except KeyError:
                            print('[!] Invalid input please enter True or False!')

    client = Client(root_dir, client_name, cmd_list=command_list, keepass_db=keepass_db, keepass_pwd=keepass_pwd)
    manager = Manager()
    report = manager.list()

    process_list = [Process(target=device.run_get_configs, args=(get_configs_info, report)) for device in client.device_list]
    [process.start() for process in process_list]
    [process.join() for process in process_list]
    
    client.report = report
    client.generate_config_report()
    client.generate_config_parsed()

    with open(f"{client.dir}/outputfiles/script_output.json", 'w') as outfile:
        json.dump(list(report), outfile, indent=2)

    if 'Network Diagram' in get_configs_info:
        client.generate_diagram()

    print(f"Execution time: {time.time() - st} seconds")
