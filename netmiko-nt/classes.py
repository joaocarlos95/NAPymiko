# -*- coding: UTF-8 -*-

import csv
import inspect
import os
import serial.tools.list_ports
import threading

from datetime import date
from N2G import yed_diagram
from netmiko import ConnectHandler, file_transfer
from netmiko.utilities import get_structured_data
from pykeepass import PyKeePass


os.environ['NTC_TEMPLATES_DIR'] = os.path.join(os.path.dirname(__file__), './submodule/ntc-templates/ntc_templates/templates')
os.environ['N2G_DIR'] = os.path.join(os.path.dirname(__file__), './submodule/N2G')

class Client:

    def __init__(self, dir, name, keepass_db=None, keepass_pwd=None):
        self.dir = f"{dir}/{name}/04. Automation"
        self.name = name
        self.keepass_db = keepass_db
        self.keepass_pwd = keepass_pwd
        self.device_list = []

        self.get_device_list(path=f"{self.dir}/inputfiles/device_list.csv") if os.path.exists(f"{self.dir}/inputfiles/device_list.csv") else self.get_device_list()

    def get_device_list(self, path=f"{os.path.dirname(__file__)}/../device_list.csv"):
        ''' Get device list from .csv file'''

        with open(path, mode='r', encoding='utf-8') as file:
            
            for row in csv.DictReader(file, skipinitialspace=True):
                if row['vendor_os'].startswith('#'): pass
                else:
                    kdbx_username, kdbx_password, kdbx_enable_secret = self.get_kdbx_credentials(row['ip_address'])
                    username = row['username'] if row['username'] != '' else kdbx_username
                    password = row['password'] if row['password'] != '' else kdbx_password
                    enable_secret = row['enable_secret'] if row['enable_secret'] != '' else kdbx_enable_secret
                    
                    device = Device(self, row['vendor_os'], row['ip_address'], username, password, enable_secret)
                    self.device_list.append(device)

                    device
    
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

    def write_csv(self, data, filename):

        current_datetime = date.today().strftime('%Y%m%d')
        with open(f"{self.dir}/outputfiles/[{current_datetime}] {filename}.csv", 'w', newline='', encoding='utf-8') as file:  
            dict_writer = csv.DictWriter(file, data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(data)

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

    def generate_output_parsed(self):
        ''' Merge the output parsed (with textfsm) from all devices '''

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
                        print(command.output_parsed)
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
    
    def run(self):
        ''' Start getting information for the client devices '''
        
        # thread_list = []
        # for device in self.device_list: 
        #     thread = threading.Thread(target=device.run(), args=())
        #     thread.setDaemon(True)
        #     thread.start()
        #     thread_list.append(thread)
        
        # for thread in thread_list: thread.join()

        for device in self.device_list: device.run()
        self.generate_output_parsed()

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
        self.command_list = []
   
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

    def serial_connection(self):

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
    
    def get_serial_port():
        ''' Get serial port to connect to the device '''

        ports = serial.tools.list_ports.comports()
        for port, description, _ in sorted(ports):
            if "USB-to-Serial Comm Port" in description: return port
        raise Exception("[!] Serial port not identified")

    def transfer_file(self, source_dir, destination_dir, source_file, destination_file, direction='put'):
        ''' Send file between python and network device (connection previously established)  '''

        print(f"[>] Sending file: {destination_dir}{source_file}")
        transfer = file_transfer(
            self.connection,
            source_file = f"{source_dir}{source_file}",
            dest_file = destination_file,
            file_system = destination_dir,
            direction = direction,
            overwrite_file = False,
        )

        if transfer['file_exists'] and not transfer['file_transferred']:
            print(f"[!] File already exists: {destination_dir}{source_file}")
        elif transfer['file_transferred']:
            print(f"[>] File transferred: {destination_dir}{source_file}")
        else:
            print(f"[!] Error copying file: {destination_dir}{source_file} [{transfer}]")

    def delete_file(self, filename, file_system='flash:'):
        ''' Delete file from the file system '''

        print(f"[>] Deleting file: {file_system}{filename}")
        output = self.connection.send_command(
            command_string=f"delete /recursive {file_system}{filename}",
            expect_string=r'Delete filename',
            strip_prompt=False,
            strip_command=False
        )
        if "Delete filename" in output:
            output += self.connection.send_command(
                command_string='\n',
                expect_string=r'confirm',
                strip_prompt=False,
                strip_command=False
            )
        if "confirm" in output:
            output += self.connection.send_command(
                command_string='y',
                expect_string=r'#',
                strip_prompt=False,
                strip_command=False
            )

    def md5_verify(self, filename, md5, file_system='flash:'):

        md5_checksum = self.run_command(f"verify /md5 {file_system}{filename}").split("= ")[1].strip()
        md5_status = (md5 == md5_checksum)

        if md5_status:
            print('[>] MD5 status: Ok')
        else:
            print('[!] MD5 status: NOk')

        return md5_status

    def upgrade(self, filename, file_system='flash:'):

        print(f"[>] Changing boot variable: {file_system}{filename}")
        self.run_command('no boot system', config_mode=True)
        self.run_command(f"boot system {file_system}{filename}", config_mode=True)
        
        boot_path = self.run_command('show boot', textfsm=True)[0]['boot_path']
        if not boot_path == f"{file_system}{filename}":
            print(f"[!] Boot variable inconsistance: {boot_path}")


        print('[>] Saving configuration')
        self.connection.save_config()

        print('[>] Rebooting')
        self.connection.send_command('reload', expect_string=r'confirm')
        self.connection.send_command('\n')

    def run(self):
        ''' Execute all commands for the device '''

        for command in self.command_list:
            command.run()

class Commands():

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
            self.device.ssh_connect()
            
        except Exception as exception:
            if '[WinError 10061] No connection could be made because the target machine actively refused it' in str(exception):
                try:
                    self.device.telnet_connect()
                
                except Exception as exception:
                    self.status = "Couldn't connect to the device"
                    raise Exception(f"[!] Couldn't connect to the device with IP {self.device.ip_address}")
            else:
                self.status = exception

        try:
            if config_mode:
                print(f"[>] Applying configuration command: {self.command}")
                self.device.connection.config_mode()
                self.output = self.device.connection.send_config_set(self.command)
                self.device.connection.exit_config_mode()
                self.status = 'Done'
            else:
                print(f"[>] Running show command: {self.command}")
                self.output = self.device.connection.send_command(self.command, delay_factor=10, read_timeout=600)
                self.output_parsed = get_structured_data(self.output, platform=self.device.vendor_os, command=self.command)

                if type(self.output_parsed) == list: self.status = 'Done'
                elif 'Invalid input detected' in self.output: self.status = 'Command not found'
                elif type(self.output_parsed) == str and self.textfsm: self.status = 'Error parsing the output'
           
        except Exception as exception:
                self.status = exception
        
        self.device.connection.disconnect()
        self.save_output()

    def save_output(self):
        ''' Save in a text file the output of the command '''

        os.makedirs(f"{self.device.client.dir}/outputfiles/{self.info}", exist_ok = True)

        current_datetime = date.today().strftime('%Y%m%d')
        filename = f"[{current_datetime}] {self.device.hostname} ({self.device.ip_address}) - {self.command.replace(' ', '_')}.txt"
        with open(f"{self.device.client.dir}/outputfiles/{self.info}/{filename}", mode='w', encoding='utf-8') as file:
            file.write(self.output)