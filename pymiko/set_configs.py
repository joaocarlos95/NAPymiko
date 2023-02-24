# -*- coding: UTF-8 -*-

import json
import os
import sys
import time
from multiprocessing import Manager, Process
from classes import Client


def raise_exception(exception):
    sys.exit(f"[!] {exception}")


if __name__ == '__main__':
    st = time.time()

    with open(os.path.join(os.path.dirname(__file__), './set_configs.txt'), 'r', encoding='utf-8') as file:     
        set_configs_info = []
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
                    keepass_pwd = input('[>] Keepass password: ')
            elif '[x]' in line or '[X]' in line:
                info_requested = line.split('] ')[1].rstrip()
                set_configs_info.append(info_requested)
            
    client = Client(root_dir, client_name, keepass_db=keepass_db, keepass_pwd=keepass_pwd)
    manager = Manager()
    report = manager.list()

    process_list = [Process(target=device.run_set_configs, args=(set_configs_info, report)) for device in client.device_list]
    [process.start() for process in process_list]
    [process.join() for process in process_list]
    
    client.report = report
    client.generate_config_report()
    client.generate_config_parsed()

    with open(f"{client.dir}/outputfiles/script_output_set.json", 'w') as outfile:
        json.dump(list(report), outfile, indent=2)

    print(f"Execution time: {time.time() - st} seconds")
