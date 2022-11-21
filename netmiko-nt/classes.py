# -*- coding: UTF-8 -*-

import csv
import ftplib
import inspect
import json
import os
import re
import serial.tools.list_ports
import threading
import yaml

from datetime import date
from jinja2 import Environment, FileSystemLoader
from N2G import yed_diagram
from netmiko import ConnectHandler, file_transfer
from netmiko.utilities import get_structured_data
from pykeepass import PyKeePass

os.environ['NTC_TEMPLATES_DIR'] = os.path.join(os.path.dirname(__file__), './submodule/ntc-templates/ntc_templates/templates')
os.environ['N2G_DIR'] = os.path.join(os.path.dirname(__file__), './submodule/N2G')


class Client:

    def __init__(self, dir, name, keepass_db=None, keepass_pwd=None, ftp_server=None):
        self.dir = f"{dir}/{name}/04. Automation"
        self.name = name
        self.keepass_db = keepass_db
        self.keepass_pwd = keepass_pwd
        self.device_list = []
        self.upgrade_list = None
        self.ftp_server = ftp_server

        self.get_device_list()

    def generate_config(self):

        path = f"{self.dir}/inputfiles/configuration.yaml" if os.path.exists(f"{self.dir}/inputfiles/configuration.yaml") else f"{os.path.dirname(__file__)}/../configuration.yaml"

        env = Environment(loader = FileSystemLoader(f"{os.path.dirname(__file__)}/submodule/jinja2_templates"), trim_blocks=True, lstrip_blocks=True)
        j2_template = env.get_template('base_config.j2')

        with open(path, mode='r', encoding='utf-8') as file: data = yaml.load(file, Loader=yaml.SafeLoader)

        vendor_os = data['vendor_os']
        del data['vendor_os']
        configuration = j2_template.render(data, vendor_os=vendor_os, config_blocks=data.keys())
        print(configuration)

    def generate_diagram(self):
        ''' Generate network diagram in drawio format, based on CDP neighbors '''

        diagram = yed_diagram()
        graph = {
            'nodes': [],
            'links': []
        }
        
        for device in self.device_list:
            graph['nodes'].append({
                'id': device.ip_address, 
                'top_label': device.hostname
            })
            
            for command in device.command_list:
                if 'Network Diagram' in command.info:
                    for neighbor in command.output_parsed:
                        graph['nodes'].append({
                            'id': neighbor['management_ip'],
                            'top_label': neighbor['destination_host'],
                            'bottom_label': neighbor['platform'],
                            'description': f"capabilities: {neighbor['capabilities']}"
                        })
                        graph['links'].append({
                            'source': device.ip_address, 
                            'target': neighbor['management_ip'],
                            'src_label': neighbor['local_port'],
                            'trgt_label': neighbor['remote_port']
                        })

        diagram.from_dict(graph)
        diagram.layout(algo='tree')

        print('[>] Generating Network Diagram')
        current_datetime = date.today().strftime('%Y%m%d')
        diagram.dump_file(filename=f"[{current_datetime}] Network Diagram.graphml", folder=f"{self.dir}/outputfiles")

    def generate_output_parsed(self):
        ''' Merge textfsm output from all devices in a single .csv file '''

        textfsm_output = {}
        for device in self.device_list:
            for command in device.command_list:
                for output_parsed in command.output_parsed:
                    if type(output_parsed) != str:
                        textfsm_output.setdefault(command.info, [])
                        textfsm_output[command.info].append(({
                            'device_hostname': device.hostname,
                            'device_ip_address': device.ip_address,
                            **output_parsed
                        }))

        for info, output_parsed in textfsm_output.items(): self.write_csv(output_parsed, filename=info)

    def generate_report(self):
        ''' Generate report of commands executed '''

        report = []
        for device in self.device_list:
            for command in device.command_list:
                report.append({
                    'device_hostname': device.hostname,
                    'device_ip_address': device.ip_address,
                    'info': command.info,
                    'command': command.command,
                    'status': command.status
                })

        self.write_csv(report, filename='Report')

    def get_device_list(self):
        ''' Get device list from .csv file'''

        path = f"{self.dir}/inputfiles/device_list.csv" if os.path.exists(f"{self.dir}/inputfiles/device_list.csv") else f"{os.path.dirname(__file__)}/../device_list.csv"
        with open(path, mode='r', encoding='utf-8') as file:
            
            for row in csv.DictReader(file, skipinitialspace=True):
                if row['vendor_os'].startswith('#'): pass
                else:
                    if row['username'] != '' and row['password'] != '':
                        username = row['username'] if row['username'] != '' else kdbx_username
                        password = row['password']
                        enable_secret = row['enable_secret']

                    else:
                        try:
                            kdbx_username, kdbx_password, kdbx_enable_secret = self.get_kdbx_credentials(row['ip_address'])
                            username = kdbx_username
                            password = kdbx_password
                            enable_secret = kdbx_enable_secret

                        except Exception as exception:
                                if "[!] Couldn't find credentials" in str(exception):
                                    username = None
                                    password = None
                                    enable_secret = None
                                    print("ERROR KEEPASS " + exception)
                                else:
                                    raise exception

                    device = Device(self, row['vendor_os'], row['ip_address'], username, password, enable_secret)
                    self.device_list.append(device)

    def get_kdbx_credentials(self, ip_address):
    
        try:
            keepass = PyKeePass(self.keepass_db, self.keepass_pwd)

        except Exception as exception:
            if 'No such file or directory:' in str(exception):
                raise Exception('[!] Error getting keepass database')
            elif len(str(exception)) == 0:
                raise Exception('[!] Wrong keepass password')
            else:
                raise Exception(f"[!] Error in {inspect.currentframe().f_code.co_name}", exception)

        group = keepass.find_groups(name=self.name, first=True)
        if not group:
            raise Exception(f"[!] Group {self.name} doesn't exist")
        
        entry = keepass.find_entries(group=group, url=ip_address, tags=['SSH', 'Telnet'], recursive=True, first=True)
        if not entry:
            entry = keepass.find_entries(group=group, title='[Common]', first=True)
            if not entry:
                entry = keepass.find_entries(group=group, title='[Common]', first=True)
                if not entry:
                    raise Exception(f"[!] Couldn't find credentials for {ip_address}")

        return entry.username, entry.password, ''

    def get_upgrade_list(self):
        ''' Get image info from .csv file'''

        path = f"{self.dir}/inputfiles/upgrade_list.csv" if os.path.exists(f"{self.dir}/inputfiles/upgrade_list.csv") else f"{os.path.dirname(__file__)}/../upgrade_list.csv"
        with open(path, mode='r', encoding='utf-8') as file:
            
            for row in csv.DictReader(file, skipinitialspace=True):
                if row['vendor_os'].startswith('#'): pass
                else:
                    if row['username'] != '' and row['password'] != '':
                        username = row['username'] if row['username'] != '' else kdbx_username
                        password = row['password']
                        enable_secret = row['enable_secret']

                    else:
                        try:
                            kdbx_username, kdbx_password, kdbx_enable_secret = self.get_kdbx_credentials(row['ip_address'])
                            username = kdbx_username
                            password = kdbx_password
                            enable_secret = kdbx_enable_secret

                        except Exception as exception:
                                if "[!] Couldn't find credentials" in str(exception):
                                    username = None
                                    password = None
                                    enable_secret = None
                                    print(exception)
                                else:
                                    raise exception

                    device = Device(self, row['vendor_os'], row['ip_address'], username, password, enable_secret)
                    self.device_list.append(device)

    def run(self):
        ''' Start getting information for the client devices '''
        
        # thread_list = []
        # for device in self.device_list: 
        #     thread = threading.Thread(target=device.run(), args=())
        #     thread.setDaemon(True)
        #     thread.start()
        #     thread_list.append(thread)
        
        # for thread in thread_list: thread.join()

        for device in self.device_list:
            device.run()
            device.connect()

    def write_csv(self, data, filename):

        current_datetime = date.today().strftime('%Y%m%d')
        with open(f"{self.dir}/outputfiles/[{current_datetime}] {filename}.csv", 'w', newline='', encoding='utf-8') as file:  
            dict_writer = csv.DictWriter(file, data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(data)


class Device():

    def __init__(self, client, vendor_os, ip_address, username, password, enable_secret=None):
        self.client = client
        self.vendor_os = vendor_os
        self.hostname = None
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.enable_secret = enable_secret
        self.connection = None
        self.configuration = None
        self.command_list = []
        self.upgrade_list = []
    
    def connect(self):
        ''' Connect to the device '''

        try:
            self.ssh_connect()
            
        except Exception as exception:
            if '[WinError 10061] No connection could be made because the target machine actively refused it' in str(exception):
                try:
                    self.telnet_connect()
                
                except Exception as exception:
                    raise Exception(f"[!] Couldn't connect to the device with IP {self.ip_address}")
            else:
                raise Exception(f"[!] CONNECT ERROR {exception}")

    def delete_file(self, flash, file):
        ''' Delete file from the flash '''

        print(f"[>] Deleting file {flash}{file} from {self.hostname} ({self.ip_address})")      
        output = self.connection.send_command(command_string=f"delete /recursive {flash}{file}", expect_string=r'Delete filename', strip_prompt=False, strip_command=False)
        if "Delete filename" in output:
            output += self.connection.send_command(command_string='\n', expect_string=r'confirm', strip_prompt=False, strip_command=False)
        if "confirm" in output:
            output += self.connection.send_command(command_string='y', expect_string=r'#', strip_prompt=False, strip_command=False)

    def disconnect(self):
        ''' Disconnect from the device '''

        self.connection.disconnect()

    def get_command(self, info, command, textfsm):
        ''' Create a Command object '''

        return Command(self, info, command, textfsm)

    def get_configs(self, get_configs_info):
        ''' Get device configuration from pre-defined command list '''

        with open(f"{os.path.dirname(__file__)}/commands.json", 'r', encoding='utf-8') as commands:
            command_list = json.load(commands)
    
        for info, commands in command_list.items():
            if info in get_configs_info:
                for command in commands['commands'][self.vendor_os]:
                    self.command_list.append(self.get_command(info, command, commands['textfsm']))
        
        self.run()

    def get_serial_port():
        ''' Get serial port to connect to the device '''

        ports = serial.tools.list_ports.comports()
        for port, description, _ in sorted(ports):
            if "USB-to-Serial Comm Port" in description: return port
        raise Exception("[!] Serial port not identified")

    def md5_verify(self, flash, file, md5_checksum, target_md5_checksum):
        ''' Verify MD5 checksum '''

        md5_checksum = self.run_command(f"verify /md5 {file_system}{filename}").split("= ")[1].strip()
        return target_md5_checksum == md5_checksum

    def run(self):
        ''' Execute all commands for the device '''
        
        self.connect()
        for command in self.command_list:
            command.run()

    def send_file(self, source, destination, file):
        ''' Copy file from source to destination '''

        print(f"[>] Copying {source.split('@')[1]}{file} to {destination} from the device {self.hostname} ({self.ip_address})")
        output = self.connection.send_command(command_string=f"copy {source}{file} {destination}{file}", expect_string=r'Destination filename', strip_prompt=False, strip_command=False)
        if "Destination filename" in output:
            output += self.connection.send_command(command_string='\n', expect_string=r'#', strip_prompt=False, strip_command=False, read_timeout=600)
        print(f"[>] File {file} copied to {destination}")

    def serial_connect(self):

        serial_port = self.get_serial_port()
        serial_connection = ConnectHandler(
            device_type = f"{self.vendor_os}_serial",
            username = self.username,
            password = self.password,
            fast_cli = False,
            conn_timeout = 30,
            serial_settings = {
                "baudrate": serial.Serial.BAUDRATES[12],
                "bytesize": serial.EIGHTBITS,
                "parity": serial.PARITY_NONE,
                "stopbits": serial.STOPBITS_ONE,
                "port": serial_port,
            },
        )
        if not self.connection.check_enable_mode():
            self.connection.secret = self.enable_secret
            self.connection.enable()

        self.hostname = self.connection.find_prompt()[:-1]
        print(f"[>] Connected to: {self.hostname} (serial port)")

    def ssh_connect(self):
        ''' Establish a SSH connection with the device '''

        self.connection = ConnectHandler(
            device_type = self.vendor_os,
            ip = self.ip_address, 
            username = self.username,
            password = self.password,
            banner_timeout = 10,
        )
        if not self.connection.check_enable_mode():
            self.connection.secret = self.enable_secret
            self.connection.enable()
        
        self.hostname = self.connection.find_prompt()[:-1]
        print(f"[>] Connecting to: {self.hostname} ({self.ip_address})")

    def telnet_connect(self):
        ''' Establish a Telnet connection with the device '''

        self.connection = ConnectHandler(
            device_type = f"{self.vendor_os}_telnet",
            ip = self.ip_address,
            username = self.username,
            password = self.password,
            banner_timeout = 10,
        )
        if not self.connection.check_enable_mode():
            self.connection.secret = self.enable_secret
            self.connection.enable()

        self.hostname = self.connection.find_prompt()[:-1]
        print(f"[>] Connected to: {self.hostname} ({self.ip_address})")

    def run_upgrade(self, upgrade_steps):
        ''' Initiate the uprade process of the device/stack devices '''

        for command in self.command_list:

            # Get current version and hardware information
            if command.info == 'Device Information':
                current_release = command.output_parsed[0]['version']
                running_image = command.output_parsed[0]['running_image']
                hardware_list = command.output_parsed[0]['hardware']
            
            # Get all memory flashes from the device (1 for standlone device; X for stack devices) and append it in a list
            elif command.info == 'File System':
                flash_list = {}
                # Flashes designation for cisco_ios and cisco_nxos
                if self.vendor_os == 'cisco_ios' or self.vendor_os == 'cisco_nxos':
                    for flash in command.output.split('\n'):
                        flash_id = re.search('flash:|flash-\d:|flash\d:', flash)
                        if flash_id: flash_list[flash_id.group()] = {
                            'free_space': None,
                            'files': []
                        }
                else:
                    raise Exception(f"[!] Code not developed dor current vendor_os ({self.vendor_os})")

        upgrade = Upgrade(self, upgrade_steps, current_release, running_image, hardware_list, flash_list)
        upgrade.run()
        self.upgrade_list.append(upgrade)
        

class Command():

    def __init__(self, device, info, command, textfsm):
        self.device = device
        self.info = info
        self.command = command
        self.output = None
        self.textfsm = textfsm
        self.output_parsed = None
        self.status = None

    def run(self, config_mode=False):
        ''' Connect to a given device and run the requested command '''

        try:
            if config_mode:
                print(f"[>] Applying configuration command: {self.command}")
                self.device.connection.config_mode()
                self.output = self.device.connection.send_config_set(self.command)
                self.device.connection.exit_config_mode()
                self.status = 'Done'
            else:
                print(f"[>] Running command: {self.command}")
                self.output = self.device.connection.send_command(self.command, delay_factor=10, read_timeout=600)
                self.output_parsed = get_structured_data(self.output, platform=self.device.vendor_os, command=self.command)

                if type(self.output_parsed) == list: self.status = 'Done'
                elif 'Invalid input detected' in self.output: self.status = 'Command not found'
                elif type(self.output_parsed) == str and self.textfsm: self.status = 'Error parsing the output'
           
        except Exception as exception:
                self.status = exception
        
        self.save_output()

    def save_output(self):
        ''' Save in a text file the output of the command '''

        os.makedirs(f"{self.device.client.dir}/outputfiles/{self.info}", exist_ok = True)

        current_datetime = date.today().strftime('%Y%m%d')
        filename = f"[{current_datetime}] {self.device.hostname} ({self.device.ip_address}) - {self.command.replace(' ', '_')}.txt"
        with open(f"{self.device.client.dir}/outputfiles/{self.info}/{filename}", mode='w', encoding='utf-8') as file:
            file.write(self.output)


class Upgrade():

    def __init__(self, device, upgrade_steps, current_release, running_image, hardware_list, flash_list):
        self.device = device
        self.upgrade_steps = upgrade_steps
        self.current_release = current_release
        self.running_image = running_image
        self.mode = 'Bundle' if running_image.endswith('.bin') else 'Install'
        self.target_image = None
        self.target_release = None
        self.image_space = None
        self.image_md5 = None
        self.hardware_list = hardware_list
        self.flash_list = flash_list    # dict(key: flash_id; value: dict(keys: [free_space, files]))
        self.status = None

        self.get_target_release_info()
        self.get_dir_info()

    def delete_old_images(self, flash):
        ''' Delete old images that are not being used '''

        for file in self.flash_list[flash]['files']:
            if file != self.running_image and file != self.target_image and file.endswith('.bin'):
                self.device.delete_file(flash, file)

    def get_dir_info(self):
        ''' Get free space from all memory flashes '''

        with open(f"{os.path.dirname(__file__)}/commands.json", 'r', encoding='utf-8') as commands:
            command_list = json.load(commands)

        for flash, info in self.flash_list.items():

            command = f"{command_list['Device Directory']['commands'][self.device.vendor_os][0]} {flash}"
            command_obj = self.device.get_command('Device Directory', command, command_list['Device Directory']['textfsm'])
            command_obj.run()

            file_list = []
            for file in command_obj.output_parsed:
                file_list.append(file['name'])
            
            self.flash_list[flash]['free_space'] = file['total_free']
            self.flash_list[flash]['files'] = file_list

    def get_target_release_info(self):
        ''' Get target release image information '''

        # Load software image information
        with open(f"{os.path.dirname(__file__)}/os_images.json", 'r', encoding='utf-8') as os_images: 
            os_image_list = json.load(os_images)

        # Get client target software information
        path = f"{self.device.client.dir}/inputfiles/upgrade_list.csv" if os.path.exists(f"{self.device.client.dir}/inputfiles/upgrade_list.csv") else f"{os.path.dirname(__file__)}/../upgrade_list.csv"
        with open(path, mode='r', encoding='utf-8') as file:

            for row in csv.DictReader(file, skipinitialspace=True):
                if row['model'] in self.hardware_list:
                    self.target_release = row['target_release']
                    self.target_image = os_image_list[self.device.vendor_os][self.hardware_list[0]][self.target_release]['image']
                    self.image_space = os_image_list[self.device.vendor_os][self.hardware_list[0]][self.target_release]['space']
                    self.image_md5 = os_image_list[self.device.vendor_os][self.hardware_list[0]][self.target_release]['md5']

    def has_space(self, flash):
        ''' Check if flash as enough space for target image '''
        
        # Flash has enough space for the target image
        if int(self.flash_list[flash]['free_space']) - int(self.image_space) > 0:
            return True
        
        # Flash does not have enough space for the target image
        else:
            print(f"[!] Device {self.device.hostname} ({self.device.ip_address}) has no available space in {flash}")
            self.status = f"No available space in {flash}"
            return False 

    def transfer_image(self):
        ''' Transfer image to device flash '''

        # Check if current image is the running image of the device
        if self.current_release == self.target_release:
            self.status = f"Device already with target release: {self.target_release}"
            print(f"[!] Device {self.device.hostname} ({self.device.ip_address}) already upgraded to {self.target_release}")
            return
       
        # Check if target image is already in all flashes
        flash_list_copy = self.flash_list.copy()
        for flash, info in self.flash_list.items():
            # Ignore flashes that already have the image
            if self.target_image in info['files']:
                del flash_list_copy[flash]      # flash_list_copy contains all flashes that doesn't have the target image
        
        # Check for the model Cisco C2960, if the image is not present in all stack members
        if any('2960' in hardware for hardware in self.hardware_list):
            # Target image is not present in standalone switch flash 
            if flash_list_copy.keys() == self.flash_list.keys() and len(flash_list_copy.keys()) == 1:
                flash = list(self.flash_list.keys())[0]
                if self.has_space(flash):
                    self.device.send_file(f"ftp://{self.device.client.ftp_server}", flash, self.target_image)
                else:
                    self.delete_old_images(list(flash_list_copy.keys())[0])
                    self.get_dir_info()
                    if self.has_space(flash):
                        self.device.send_file(f"ftp://{self.device.client.ftp_server}", flash, self.target_image)
                    else:
                        raise Exception('[!] ERROR NOT ENOUGH SPACE TO COPY FILES')
            # Target image only present in some of the devices
            elif len(flash_list_copy.keys()) != 0:
                flash_with_target_image = list(set(self.flash_list.keys()) - set(flash_list_copy.keys()))[0]
                # Copy target image to the remaining flashes
                for flash in flash_list_copy:
                    if self.has_space(flash):
                        self.device.send_file(flash_with_target_image, flash, self.target_image)
                    else:
                        self.delete_old_images(list(flash_list_copy.keys())[0])
                        self.get_dir_info()
                        if self.has_space(flash):
                            self.device.send_file(flash_with_target_image, flash, self.target_image)
                        else:
                            raise Exception('[!] ERROR NOT ENOUGH SPACE TO COPY FILES')

        # Image is present in all flashes
        if len(flash_list_copy) == 0:
            print(f"[>] Image {self.target_image} already in: {' '.join(self.flash_list.keys())}")
            return

    def run(self):

        if 'Transfer Image' in self.upgrade_steps:
            self.transfer_image()
        elif 'Verify MD5' in self.upgrade_steps:
            self.verify_image_integrity()

        # print(f"[>] Changing boot variable: {file_system}{filename}")
        # self.run_command('no boot system', config_mode=True)
        # self.run_command(f"boot system {file_system}{filename}", config_mode=True)
        
        # boot_path = self.run_command('show boot', textfsm=True)[0]['boot_path']
        # if not boot_path == f"{file_system}{filename}":
        #     print(f"[!] Boot variable inconsistance: {boot_path}")


        # print('[>] Saving configuration')
        # self.connection.save_config()

        # print('[>] Rebooting')
        # self.connection.send_command('reload', expect_string=r'confirm')
        # self.connection.send_command('\n')