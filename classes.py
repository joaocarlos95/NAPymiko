# -*- coding: UTF-8 -*-

import copy
import csv
import ftplib
import inspect
import json
import os
import re
import serial.tools.list_ports
import sys
import threading
import time
import yaml

from datetime import date
from jinja2 import Environment, FileSystemLoader
from multiprocessing import Process
from N2G import yed_diagram
from netmiko import ConnectHandler, file_transfer
from netmiko.utilities import get_structured_data
from OuiLookup import OuiLookup
from pykeepass import PyKeePass
from random import randrange

os.environ['NET_TEXTFSM'] = os.path.join(os.path.dirname(__file__), 'dep/ntc-templates/ntc_templates/templates')

# Load software image information
with open(f"{os.path.dirname(__file__)}/json_files/os_images.json", 'r', encoding='utf-8') as imgs: 
    OS_IMAGE_LIST = json.load(imgs)

COMMAND_LIST = None

class Client:

    def __init__(self, dir, name, cmd_list=None, keepass_db=None, keepass_pwd=None, ftp_server=None):
        self.dir = dir
        self.name = name
        self.keepass_db = keepass_db
        self.keepass_pwd = keepass_pwd
        self.device_list = []
        self.dev_list = []
        self.upgrade_list = None
        self.ftp_server = ftp_server
        self.report = None

        global COMMAND_LIST
        COMMAND_LIST = cmd_list

        self.get_devices_from_csv()

    # def generate_config(self):

    #     path = f"{self.dir}/inputfiles/configuration.yaml" if os.path.exists(f"{self.dir}/inputfiles/configuration.yaml") else f"{os.path.dirname(__file__)}/../configuration.yaml"

    #     env = Environment(loader = FileSystemLoader(f"{os.path.dirname(__file__)}/submodule/jinja2_templates"), trim_blocks=True, lstrip_blocks=True)
    #     j2_template = env.get_template('base_config.j2')

    #     with open(path, mode='r', encoding='utf-8') as file: data = yaml.load(file, Loader=yaml.SafeLoader)

    #     vendor_os = data['vendor_os']
    #     del data['vendor_os']
    #     configuration = j2_template.render(data, vendor_os=vendor_os, config_blocks=data.keys())
    #     print(configuration)

    def generate_diagram(self):
        ''' Generate network diagram in drawio format, based on CDP neighbors '''

        diagram = yed_diagram()
        graph = {
            'nodes': [],
            'links': []
        }
        
        for device in self.report:
            graph['nodes'].append({
                'id': device['ip_address'], 
                'top_label': device['hostname']
            })
            for command in device['command_list']:
                if 'Network Diagram' in command['info']:
                    for neighbor in command['output_parsed']:
                        graph['nodes'].append({
                            'id': neighbor['management_ip'],
                            'top_label': neighbor['destination_host'],
                            'bottom_label': neighbor['platform'],
                            'description': f"capabilities: {neighbor['capabilities']}"
                        })
                        graph['links'].append({
                            'source': device['ip_address'], 
                            'target': neighbor['management_ip'],
                            'src_label': neighbor['local_port'],
                            'trgt_label': neighbor['remote_port']
                        })

        diagram.from_dict(graph)
        diagram.layout(algo='tree')

        print('[>] Generating Network Diagram')
        current_datetime = date.today().strftime('%Y%m%d')
        diagram.dump_file(filename=f"[{current_datetime}] Network Diagram.graphml", folder=f"{self.dir}/outputfiles")

    def generate_config_parsed(self):
        ''' Merge textfsm output from all devices in a single .csv file '''

        print('[>] Generating configuration parsed report')
        textfsm_output = {}
        for device in self.report:
            for command in device['command_list']:
                if command['output_parsed'] != None:
                    for output_parsed in command['output_parsed']:
                        if type(output_parsed) != str:
                            textfsm_output.setdefault(command['info'], [])
                            textfsm_output[command['info']].append(({
                                'device_hostname': device['hostname'],
                                'device_ip_address': device['ip_address'],
                                **output_parsed
                            }))

        for info, output_parsed in textfsm_output.items():
            self.write_csv(output_parsed, filename=info)

    def generate_config_report(self):
        ''' Generate report for commands executed on the device'''

        print('[>] Generating configuration report')
        report = []
        for device in self.report:
            # For each command runned on a device, create a new .csv row
            if device['command_list'] == []:
                report.append({
                    'device_hostname': device['hostname'],
                    'device_ip_address': device['ip_address'],
                    'info': '',
                    'command': '',
                    'status': device['status']
                })
            for command in device['command_list']:
                if command['status'] == None:
                    status = device['status']
                else:
                    status = command['status']
                report.append({
                    'device_hostname': device['hostname'],
                    'device_ip_address': device['ip_address'],
                    'info': command['info'],
                    'command': command['command'],
                    'status': status
                })

        self.write_csv(report, filename='Configuration Report')

    def generate_upgrade_report(self):
        ''' Generate report for devices upgrade process '''

        print('[>] Generating upgrade report')
        report = []
        for device in self.report:
            # For each command runned on the device, create a new .csv row
            for upgrade in device['upgrade_list']:

                # Authentication to the device failed
                if 'Authentication failed' in upgrade['status']:
                    current_release = None
                # Devices with success login
                else:
                    current_release = upgrade['current_release']['version']
                
                # Devices not in scope
                if upgrade['target_release'] == None:
                    target_release = None
                # Devices in scope
                else:
                    target_release = upgrade['target_release']['version']
                
                report.append({
                    'device_hostname': device['hostname'],
                    'device_ip_address': device['ip_address'],
                    'step': upgrade['step'],
                    'current_release': current_release,
                    'target_release': target_release,
                    'status': upgrade['status']
                })

        self.write_csv(report, filename='Upgrade Report')

    def get_devices_from_csv(self):
        ''' Get device list from .csv file and create a device object with the information
            collected from the .csv and keepass databse (if applicable) '''

        # Load client devices information from .csv file
        if os.path.exists(f"{self.dir}/inputfiles/device_list.csv"):
            path = f"{self.dir}/inputfiles/device_list.csv"
        else:
            path = f"{os.path.dirname(__file__)}/inputfiles/device_list.csv"

        with open(path, mode='r', encoding='utf-8') as file:
            for row in csv.DictReader(file, skipinitialspace=True,):
                # Ignore devices commented
                if row['vendor_os'].startswith('#'):
                    continue
                else:
                    # Check credentials given in the .csv file (higher priority)
                    if row['username'] != '' and row['password'] != '':
                        credentials = {
                            'username': row['username'],
                            'password': row['password'],
                            'enable_secret': row['enable_secret']
                        }                   
                    # Use credentials given on the .kdbx file
                    else:
                        try:
                            credentials = self.get_kdbx_credentials(row['ip_address'])
                        except Exception as exception:
                                # Couldn't find credentials neither in .csv file nor .kdbx file
                                if "[!] Couldn't find credentials" in str(exception):
                                    credentials = {
                                        'username': None,
                                        'password': None,
                                        'enable_secret': None
                                    }
                                else:
                                    raise exception
                
                device = Device(self, *[row['vendor_os'], row['ip_address'], credentials])
                self.device_list.append(device)

    # TO BE DONE: Get enable secret from keepass database
    def get_kdbx_credentials(self, ip_address):
        ''' Get device credentials from keepass database '''
    
        try:
            # Load .kdbx file
            keepass = PyKeePass(self.keepass_db, self.keepass_pwd)
        except Exception as exception:
            if 'No such file or directory:' in str(exception):
                print('[!] Error getting keepass database)')
                raise Exception('[!] Error getting keepass database')
            elif len(str(exception)) == 0:
                print('[!] Wrong keepass password')
                raise Exception('[!] Wrong keepass password')
            else:
                raise Exception(f"Error in {inspect.currentframe().f_code.co_name}", exception)

        # Find client group within keepass, using its name
        group = keepass.find_groups(name=self.name, first=True)
        if not group:
            print(f"[!] Group {self.name} doesn't exist in keepass database")
            raise Exception(f"[!] Group {self.name} doesn't exist in keepass database")
        
        # Find device credentials, using its ip address 
        entry = keepass.find_entries(group=group, url=ip_address, tags=['SSH', 'Telnet'], \
            recursive=True, first=True)
        if not entry:
            # Find device credentials, using common entry (usually credentials for all devices)
            entry = keepass.find_entries(group=group, title='[Common]', first=True)
            if not entry:
                print(f"[!] Couldn't find credentials for device with IP: {ip_address}")
                raise Exception(f"[!] Couldn't find credentials for device with IP: {ip_address}")

        credentials = {
            'username': entry.username,
            'password': entry.password,
            'enable_secret': None
        }
        return credentials

    def write_csv(self, data, filename):
        ''' Write data in a .csv file ''' 

        # Create .csv filename
        current_datetime = date.today().strftime('%Y%m%d')
        path = f"{self.dir}/outputfiles/[{current_datetime}] {filename}.csv"

        with open(path, 'w', newline='', encoding='utf-8') as file:  
            dict_writer = csv.DictWriter(file, data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(data)


class Device():

    def __init__(self, client, vendor_os, ip_address, credentials):
        self.client = client
        self.vendor_os = vendor_os
        self.hardware = None
        self.flash = {}
        self.hostname = None
        self.ip_address = ip_address
        self.credentials = credentials
        self.connection = None
        self.command_list = []
        self.upgrade_list = []
        self.status = None
    
    def clear_counters(self):
        ''' Clear device counters '''

        self.connection.send_command('clear counters', expect_string=r'confirm')
        self.connection.send_command('\n')


    def connect(self, method='ssh'):
        ''' Connect to the device in the following order: SSH, Telnet '''

        def ssh_connect():
            ''' Establish a SSH connection with the device '''

            self.connection = ConnectHandler(
                device_type = self.vendor_os,
                ip = self.ip_address, 
                username = self.credentials['username'],
                password = self.credentials['password'],
                banner_timeout = 10,
            )

        def telnet_connect():
            ''' Establish a Telnet connection with the device '''

            self.connection = ConnectHandler(
                device_type = f"{self.vendor_os}_telnet",
                ip = self.ip_address,
                username = self.credentials['username'],
                password = self.credentials['password'],
                banner_timeout = 10,
            )

        try:
            # Connect to the device through SSH
            if method == 'ssh':
                ssh_connect()
            # Connect to the device through Telnet
            else:
                telnet_connect()
        except Exception as exception:
            if 'No connection could be made because the target machine actively refused it' in str(exception) or \
                'Connection refused' in str(exception):
                # Connect to the device through Telnet
                if method == 'ssh':
                    self.connect('telnet')
                else:          
                    print(f"[!] Connection refused by device with IP {self.ip_address}")
                    self.status = 'Device refused connection'
                    return
            elif 'TCP connection to device failed' in str(exception) or 'Operation timed out' in str(exception):
                if method == 'ssh':
                    self.connect('telnet')
                else:
                    print(f"[!] TCP connection failed to the device with IP {self.ip_address}")
                    self.status = 'TCP connection failed'
                    return
            elif 'Authentication to device failed' in str(exception) or 'Login failed' in str(exception):
                print(f"[!] Authentication failed to the device with IP {self.ip_address}")
                self.status = 'Authentication failed'
                return
            elif 'must be exactly 1024, 2048, 3072, or 4096 bits long' in str(exception):
                if method == 'ssh':
                    self.connect('telnet')
                else:
                    print(f"[!] Issue with the SSH keys in the device with IP {self.ip_address}")
                    self.status = 'Issue with the SSH keys'
                    return
            elif 'A connection attempt failed' in str(exception) or 'No existing session' in \
                str(exception) or "Unsupported 'device_type'" in str(exception):
                print(f"[!] Couldn't connect to the device with IP {self.ip_address}")
                self.status = "Couldn't connect"
                return
            else:
                raise Exception(f"Error in {inspect.currentframe().f_code.co_name}", exception, self.ip_address)

        # If no connection could be made exit
        if self.connection == None: return

        # If not in enable secret mode, enter the enable secret password 
        if not self.connection.check_enable_mode():
            self.connection.secret = self.credentials['enable_secret']
            self.connection.enable()

        # Get the hostname of the device 
        self.hostname = self.connection.find_prompt()[:-1]
        self.status = 'Connected'
        print(f"[>] Connected to {self.hostname} ({self.ip_address})")

    def create_command(self, info, txt_command, textfsm):
        ''' Create a Command object for the command to be issued on the device, and append it
            on the list of command objects for the device '''

        # Create a command object and append it to the command list of the device
        command = Command(self, info, txt_command, textfsm)
        self.command_list.append(command)
        return command

    def delete_file(self, flash, file):
        ''' Delete file from deviice flash '''

        print(f"[>] Deleting file {file} from {flash}")      
        output = self.connection.send_command(command_string=f"delete /recursive {flash}{file}", \
            expect_string=r'Delete filename', strip_prompt=False, strip_command=False)
        if "Delete filename" in output:
            output += self.connection.send_command(command_string='\n', expect_string=r'confirm', \
                strip_prompt=False, strip_command=False)
        else:
            print(output)
        if "confirm" in output:
            output += self.connection.send_command(command_string='y', expect_string=r'#', \
                strip_prompt=False, strip_command=False)
                
        print(f"[>] File {file} deleted")

    def disconnect(self):
        ''' Disconnect from the device '''

        # Connection to the device couln't be mande
        if self.connection == None: return

        # Disconnect from the device
        self.connection.disconnect()
        print(f"[>] Disconnected from {self.hostname} ({self.ip_address})")

    def flash_has_space(self, flash, needed_space):
        ''' Check if flash as enough space givena needed value '''
        
        # Flash has enough space
        if int(self.flash[flash]['free_space']) - needed_space > 0:
            return True
        # Flash does not have enough space
        else:
            return False

    def get_configs(self, get_configs_info):
        ''' Get device configuration from pre-defined list and create a command object for each
            command to be issued on the device '''

        for info in get_configs_info:
            for txt_command in COMMAND_LIST[info]['commands'][self.vendor_os]:
                # Create a command object and run it on the device
                command = self.create_command(info, txt_command, COMMAND_LIST[info]['textfsm'])
                command.run()
    
    def generate_report(self, report):
        ''' Get configs report for all commands issued '''

        print(f"[>] Generating report for {self.hostname} ({self.ip_address})")
        # Transform device object in dict and remove unnecessary key/values
        device_dict = self.__dict__.copy()
        del device_dict['client']
        del device_dict['credentials']
        del device_dict['connection']

        command_list = []
        for command in self.command_list:
            # Transform command object in dict and remove unnecessary key/values
            command_list_dict = command.__dict__.copy()
            del command_list_dict['device']
            command_list.append(command_list_dict)

        upgrade_list = []
        for step in self.upgrade_list:
            # Transform command object in dict and remove unnecessary key/values
            upgrade_list_dict = step.__dict__.copy()
            del upgrade_list_dict['device']
            upgrade_list.append(upgrade_list_dict)
        
        device_dict['command_list'] = command_list
        device_dict['upgrade_list'] = upgrade_list
        report.append(device_dict)

    # def get_serial_port():
    #     ''' Get serial port to connect to the device '''

    #     ports = serial.tools.list_ports.comports()
    #     for port, description, _ in sorted(ports):
    #         if "USB-to-Serial Comm Port" in description: return port
    #     raise Exception("[!] Serial port not identified")

    def md5_checksum(self, flash, file, md5sum):
        ''' Perform MD5 checksum over a file '''

        print(f"[>] Verifying integrity of file {file}")
        cmd = f"{COMMAND_LIST['MD5 Checksum']['commands'][self.vendor_os][0]} {flash}{file}"
        command = self.create_command('MD5 Checksum', cmd, COMMAND_LIST['MD5 Checksum']['textfsm'])
        command.run()

        if md5sum == command.output.split("= ")[1].strip():
            return True
        else:
            return False
    
    def run_get_configs(self, get_configs_info, report):
        ''' Initiate the process of acquire device information '''

        # Connect to the device
        self.connect()
        # Get the desired configurations
        self.get_configs(get_configs_info)
        # Disconnect from the device
        self.disconnect()
        # Generate device report and append it to the shared variable
        self.generate_report(report)           

    # TO BE DONE: Run the first validation commands only once
    def run_upgrade(self, upgrade_steps, report):
        ''' Initiate the uprade process of the device/stack devices. Upgrade steps have a specific
            order, defined in the upgrade.txt file (FIFO) '''

        # Connect to the device
        self.connect()
        # Information to be collected in advance
        for step in upgrade_steps:
            upgrade = Upgrade(self, step)
            self.upgrade_list.append(upgrade)
            upgrade.run()
        # Disconnect from the device
        self.disconnect()
        # Generate device report and append it to the shared variable
        self.generate_report(report)   

    def send_file(self, source, destination, file):
        ''' Copy file from source to destination '''

        try:
            print(f"[>] Copying file {file} to {destination}")
            output = self.connection.send_command(command_string=f"copy {source}{file} {destination}{file}", \
                expect_string=r'Destination filename', strip_prompt=False, strip_command=False)

            if 'Destination filename' in output:
                output += self.connection.send_command(command_string='\n', expect_string=r'#', \
                    strip_prompt=False, strip_command=False, delay_factor=20, read_timeout=1200)
            
            if 'Error' in output:
                print(f"[!] File {file} not copied to {destination}")
                raise Exception(output)
            
            print(f"[>] File {file} copied to {destination}")

        except Exception as exception:
            raise Exception(f"Error in {inspect.currentframe().f_code.co_name}", exception, self.ip_address)

    def set_configs(self, set_configs_info):
        ''' Get device configuration from pre-defined list and create a command object for each
            command to be issued on the device '''

        for info in set_configs_info:

            for txt_command in COMMAND_LIST[info]['commands'][self.vendor_os]:
                # Create a command object and run it on the device
                command = self.create_command(info, txt_command, COMMAND_LIST[info]['textfsm'])
                command.run()

    # def serial_connect(self):

    #     serial_port = self.get_serial_port()
    #     serial_connection = ConnectHandler(
    #         device_type = f"{self.vendor_os}_serial",
    #         username = self.username,
    #         password = self.password,
    #         fast_cli = False,
    #         conn_timeout = 30,
    #         serial_settings = {
    #             "baudrate": serial.Serial.BAUDRATES[12],
    #             "bytesize": serial.EIGHTBITS,
    #             "parity": serial.PARITY_NONE,
    #             "stopbits": serial.STOPBITS_ONE,
    #             "port": serial_port,
    #         },
    #     )
    #     if not self.connection.check_enable_mode():
    #         self.connection.secret = self.enable_secret
    #         self.connection.enable()

    #     self.hostname = self.connection.find_prompt()[:-1]
    #     print(f"[>] Connected to: {self.hostname} (serial port)")


class Command():

    def __init__(self, device, info, command, textfsm):
        self.device = device
        self.info = info
        self.command = command
        self.textfsm = textfsm
        self.output = None
        self.output_parsed = None
        self.status = None

    def get_mac_vendor(self):
        ''' Get MAC Address vendor from all devices connected to the switch '''

        for line in self.output_parsed:
            vendor = list(OuiLookup().query(line['destination_address'])[0].values())[0]
            print(vendor)
            line['vendor'] = vendor

    def run(self, config_mode=False, save_output=True):
        ''' Connect to a given device and run the requested command '''

        # Connection to the device couln't be made
        if self.device.connection == None: return
        # Reconnect to the device, since connection was closed
        elif not self.device.connection.is_alive(): self.device.connect()

        if self.info == 'Interfaces Counters':
            print('[>] Clearing counters and waiting 5 minutes...')
            #self.device.clear_counters()
            #time.sleep(300)

        try:
            # Apply configuration on the device, entering in configuration mode
            if config_mode:
                print(f"[>] Applying configuration: {self.command}")
                self.device.connection.config_mode()
                self.output = self.device.connection.send_config_set(self.command)
                self.device.connection.exit_config_mode()
            # Get configurations from the device
            else:
                print(f"[>] Getting configuration: {self.command}")
                if self.info == 'Configuration':
                    read_timeout = 600
                else:
                    read_timeout = 100
                self.output = self.device.connection.send_command(self.command, read_timeout=read_timeout)
                # Parse command output from the device
                if self.textfsm:
                    self.output_parsed = get_structured_data(self.output, \
                         platform=self.device.vendor_os, command=self.command)

                    if self.info == 'MAC Address Table':
                        self.get_mac_vendor()

            if 'Invalid input detected' in self.output:
                print(f"[!] Command not found: {self.command}")
                self.status = 'Command not found'
            elif type(self.output_parsed) == str and self.textfsm:
                print(f"[!] Error parsing the output of the command: {self.command}")
                self.status = 'Error parsing the output'
            else:
                self.status = ['Done']
           
        except Exception as exception:
            if 'Pattern not detected' in str(exception):
                print(f"[!] Pattern not detected on {self.device.ip_address} in command: {self.command}")
                self.status = f"Error getting information from command: {self.command}"
                return
            raise Exception(f"Error in {inspect.currentframe().f_code.co_name}", exception, self.device.ip_address)


    def save_output(self):
        ''' Save in a .txt file the output of the command issued on the device '''

        # Load client devices information from .csv file
        os.makedirs(f"{self.device.client.dir}/outputfiles/{self.info}", exist_ok=True)
        path = f"{self.device.client.dir}/outputfiles/{self.info}"
        
        current_datetime = date.today().strftime('%Y%m%d')
        command = self.command.replace(' ', '_').replace('/', '')
        filename = f"[{current_datetime}] {self.device.hostname} ({self.device.ip_address}) - {command}.txt"
        with open(f"{path}/{filename}", mode='w', encoding='utf-8') as file:
            file.write(f"{self.device.hostname}# {self.command}\n")
            file.write(self.output)


class Upgrade():

    def __init__(self, device, step):
        self.device = device
        self.step = step
        self.current_release = None
        self.target_release = None
        self.image_integrity = None
        self.status = None

        # Couldn't connect to the device
        if 'Authentication failed' in self.device.status:
            self.status = self.device.status
            return

        self.get_current_release_info()
        self.get_target_release_info()
        self.get_directories_info()

    def get_current_release_info(self):
        ''' Get current release information and device related information (flash(es) memories 
            and device(s) models '''

        get_configs_info = ['Device Information', 'File System']
        self.device.get_configs(get_configs_info)
           
        for command in self.device.command_list:
            # Get current release information and device hardware model(s)
            if command.info == 'Device Information':
                self.current_release = {
                    'version': command.output_parsed[0]['version'],
                    'image': command.output_parsed[0]['running_image'],
                    'mode': 'Bundle' if command.output_parsed[0]['running_image'].endswith('bin')
                        else 'Install'
                }
                self.device.hardware = command.output_parsed[0]['hardware']

            # Get all memory flashes from the device (1 for standlone device; X for stack devices)
            elif command.info == 'File System':
                for flash in command.output.split('\n'):
                    # Memory flash designation for cisco_ios and cisco_nxos
                    if self.device.vendor_os == 'cisco_ios' or self.device.vendor_os == 'cisco_nxos':
                        # Search for the following patterns in the file system
                        flash_id = re.search('flash:|flash-\d:|flash\d:', flash)
                        if flash_id:
                            self.device.flash[flash_id.group()] = {
                                'free_space': None,
                                'files': []
                            }
                    else:
                        raise Exception(f"Error in {inspect.currentframe().f_code.co_name}",
                            self.vendor_os)

    def get_directories_info(self):
        ''' Get free space from all memory flashes '''

        for flash in self.device.flash.keys():
            # Get the information (free space and files/dirs) for each flash of the device
            cmd = f"{COMMAND_LIST['Device Directory']['commands'][self.device.vendor_os][0]} {flash}"
            command = self.device.create_command('Device Directory', cmd, \
                COMMAND_LIST['Device Directory']['textfsm'])
            command.run()

            file_list = []
            # Append in a list all files/dirs for the flash
            for file in command.output_parsed:
                file_list.append(file['name'])
            
            # Update device flash information
            self.device.flash[flash]['free_space'] = file['total_free']
            self.device.flash[flash]['files'] = file_list
                            
    def get_target_release_info(self):
        ''' Get target release image information '''

        # Get client target software information
        if os.path.exists(f"{self.device.client.dir}/inputfiles/upgrade_list.csv"):
            path = f"{self.device.client.dir}/inputfiles/upgrade_list.csv"
        else:
            path = f"{os.path.dirname(__file__)}/inputfiles/upgrade_list.csv"

        with open(path, mode='r', encoding='utf-8') as file:
            for row in csv.DictReader(file, skipinitialspace=True):
                if row['model'] in self.device.hardware:
                    self.target_release = {
                        'version': row['target_release'],
                        'mode': self.current_release['mode']
                    }
                    self.target_release.update(OS_IMAGE_LIST[self.device.vendor_os]
                        [self.device.hardware[0]][row['target_release']])

        if self.target_release == None:
            print(f"[!] Device model {self.device.hardware} not in scope")
            self.status = 'Device model not in scope'

    def validations(self, validation):
        ''' Run pre validations '''

        # Get client target software information
        if os.path.exists(f"{self.device.client.dir}/inputfiles/command_list.txt"):
            path = f"{self.device.client.dir}/inputfiles/command_list.txt"
        else:
            path = f"{os.path.dirname(__file__)}/inputfiles/command_list.txt"

        # Save current configuration
        self.device.connection.save_config()

        validation_output = ''
        with open(path, mode='r', encoding='utf-8') as file:
            # For each command in command list file, run it and append the output in a variable
            for row in file:
                command = self.device.create_command(f"{validation}", \
                    row.strip(), textfsm=False)
                command.run()
                validation_output += f"{self.device.hostname}# {row.strip()}\n{command.output}\n"
        
        current_datetime = date.today().strftime('%Y%m%d')
        filename = f"[{current_datetime}] {self.device.hostname} ({self.device.ip_address}) - {validation}.txt"
        path = path.replace('/inputfiles/command_list.txt', f"/outputfiles/{validation}/{filename}")
        # Save the command list output in a file
        with open(path, mode='w+', encoding='utf-8') as file:
            file.write(validation_output)

    def release_flash_memory(self, flash):
        ''' Delete old images that are not being used '''

        # Remove old files in Bundle mode
        if self.current_release['mode'] == 'Bundle':
            for file in self.device.flash[flash]['files']:
                # Remove .bin files that are not the running image nor the target image
                if self.target_release == None:
                    return
                if file != (self.current_release['image'] or self.target_release['image']) and \
                    file.endswith('.bin'):
                    self.device.delete_file(flash, file)
        # Remove old files in Install mode
        else:
            # Get version of the inactive files
            output = self.device.connection.send_command(command_string=f"show install active")
            for line in output.split('\n'):
                if 'IMG' in line:
                    # Get the version of the inactive files
                    version = '.'.join(line.split()[-1].split('.')[:-2])
                    for file in self.device.flash[flash]['files']:
                        # Delete file if it's not the running version, nor the package.conf
                        if ('.bin' in file or '.pkg' in file or '.conf' in file) and \
                            version not in file and 'packages.conf' not in file:
                            self.device.delete_file(flash, file)

    def run(self):
        ''' Perform all upgrade steps, in the correct order '''

        # Copy target image to the device
        if self.step == 'Transfer Image' and self.target_release != None:
            self.transfer_image()

        # Check target image integrity
        elif self.step == 'Verify MD5' and self.target_release != None:
           self.verify_image_integrity()

        elif self.step == 'Pre-Validations' or self.step == 'Post-Validations':
            self.validations(self.step)
        
    #     # print(f"[>] Changing boot variable: {file_system}{filename}")
    #     # self.run_command('no boot system', config_mode=True)
    #     # self.run_command(f"boot system {file_system}{filename}", config_mode=True)
        
    #     # boot_path = self.run_command('show boot', textfsm=True)[0]['boot_path']
    #     # if not boot_path == f"{file_system}{filename}":
    #     #     print(f"[!] Boot variable inconsistance: {boot_path}")


    #     # print('[>] Saving configuration')
    #     # self.connection.save_config()

    #     # print('[>] Rebooting')
    #     # self.connection.send_command('reload', expect_string=r'confirm')
    #     # self.connection.send_command('\n')

    # TO BE DONE: Merge if/elif condition for C2960 models (standalone and stack image copy)
    # TO BE DONE: Split stack from non-stack devices
    # TO BE DONE: Use only 1 for cycle to go over all flashes and perform the necessary steps
    def transfer_image(self):
        ''' Transfer image to device flash '''

        '''
            STRUCTURE:
                1. Standalone + Bundle
                2. Standalone + Install
                3. Stack + Bundle
                4. Stack + Install (merge with 2. ???) 
        '''

        # Check if current image is the running image of the device
        if self.current_release['version'] in self.target_release['version']:
            print(f"[!] Device {self.device.hostname} ({self.device.ip_address}) already upgraded to {self.target_release['version']}")
            self.status = 'Already upgraded'
            return
       
        # Get the list of flashes that doesn't have the image on it
        flash_without_target_image = copy.deepcopy(self.device.flash)
        for flash, flash_data in self.device.flash.items():
            # Ignore flashes that already have the image
            if self.target_release['image'] in flash_data['files']:
                # flash_list_copy contains all flashes that doesn't have the target image
                del flash_without_target_image[flash]

        # Target image already present in switch/switch stack
        if len(flash_without_target_image) == 0:
            print(f"[>] Image {self.target_release['image']} already in {' '.join(self.device.flash.keys())}")
            self.status = 'Done'
            return

        # Upload image to standalone switch
        if len(self.device.hardware) == 1:
            flash = list(self.device.flash.keys())[0]
            self.upload_image(flash)
        # Upload image to switch stack
        else:
            print("NEEDS TO BE DONE - TRANSFER IMAGE FOR STACK DEVICES")
            # Process to transfer image to all members in cisco_os models 2960
            if self.device.vendor_os == 'cisco_ios' and any('2960' in model for model in \
                self.device.hardware):
                for flash in flash_without_target_image:
                     self.upload_image(flash)
            # Process to transfer image to remaining switch/models
            else:
                # PASSAR IMAGEM SÓ PARA A FLASH PRINCIPAL FLASH: OR BOOTFLASH:
                pass
        
        # Update status of image transfer
        if self.status == None: self.status = 'Done'

    def upload_image(self, flash):
        ''' Upload target image to the switch, performing all necessary validations in advance ''' 

        try:
            # Delete old images before copy target image to device flash 
            #self.release_flash_memory(flash)
            # Update information of device flash
            self.get_directories_info()
            if self.device.flash_has_space(flash, self.target_release['space']):
                # Copy target image to device flash
                self.device.send_file(self.device.client.ftp_server, flash, \
                    self.target_release['image'])
            else:
                print("[!] Couldn't free up some space for the target image")
                self.status = "Couldn't free up some space for the target image"
                    
        except Exception as exception:
            if 'Error opening' in str(exception):
                self.status = f"Couln't copy image {self.target_release['image']} to {flash}"  
                return

            raise Exception(f"Error in {inspect.currentframe().f_code.co_name}", exception)

    # TO BE DONE: Validations on stack devices
    def verify_image_integrity(self):
        ''' Check MD5 integrity of target images '''

        # For Bundle and Install mode, verify image integrity on device flash/flashes
        for flash, flash_data in self.device.flash.items():
            if self.target_release['image'] not in flash_data['files']:
                # Target image is not in device flash
                print(f"[!] Image {self.target_release['image']} not in {flash}")
                self.status = f"Image {self.target_release['image']} not in {flash}"
                return
            else:
                # Run MD5 checksum of the target image
                md5 = self.device.md5_checksum(flash, self.target_release['image'], \
                    self.target_release['md5'])
                if not md5:
                # File compromised
                    print(f"[!] MD5 NOk for image {flash}{self.target_release['image']}")
                    self.status = 'MD5 NOk'
                    return
                else:
                    # MD5 validated
                    print(f"[>] MD5 Ok for image {flash}{self.target_release['image']}")
                    self.status = 'Done'