#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import serial, sys
import time

from netmiko import ConnectHandler
from netmiko.utilities import get_structured_data
from networkautomation.common.input_output_files import write_info_to_txt, get_serial_port
from networkautomation.textfsm_variables import textfsm_variables as tv
from networkautomation.global_variables import global_variables as gv



# def run_serial_connection(device_type, username, password, enable_secret):

#     serial_port = get_serial_port()
#     serial_connection = ConnectHandler(
#         device_type = "{}_serial".format(device_type),
#         username = username,
#         password = password,
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
#     if not serial_connection.check_enable_mode():
#         serial_connection.secret = enable_secret
#         serial_connection.enable()
#     return serial_connection


# def run_ssh_connection(device_type, device_ip, username, password, enable_secret):

#     ssh_connection = ConnectHandler(
#         device_type = device_type,
#         ip = device_ip, 
#         username = username,
#         password = password,
#         banner_timeout = 10,    # for issue: Error reading SSH protocol banner
#     )
#     if not ssh_connection.check_enable_mode():
#         ssh_connection.secret = enable_secret
#         ssh_connection.enable()
#     return ssh_connection


# def run_telnet_connection(device_type, device_ip, username, password, enable_secret):

#     telnet_connection = ConnectHandler(
#         device_type = "{}_telnet".format(device_type),
#         ip = device_ip, 
#         username = username,
#         password = password,
#         banner_timeout = 10,    # for issue: Error reading SSH protocol banner
#     )
#     if not telnet_connection.check_enable_mode():
#         telnet_connection.secret = enable_secret
#         telnet_connection.enable()
#     return telnet_connection


# def run_command(vendor, platform, device_ip, username, password, enable_secret, command, textfsm):
#     ''' Connect to a given device and run the requested command
#     Parameters: device IP, credentials (user and password), and command to run
#     Return: output of the command '''

#     try:
        
#         device_type = "{}_{}".format(vendor, platform)
#         if gv.get_connection_method() == "serial":
#             connection = run_serial_connection(device_type, username, password, enable_secret)
#             device_ip = "serial connection"
#         if gv.get_connection_method() == "telnet":
#             connection = run_telnet_connection(device_type, device_ip, username, password, enable_secret)
#         else:
#             connection = run_ssh_connection(device_type, device_ip, username, password, enable_secret)

#         hostname = connection.find_prompt()[:-1]
#         device_id = "{} ({})".format(hostname, device_ip)
#         print("[>] Logging into the device: {}".format(device_id))
        
#         print("[>] Running command: {}".format(command))
#         raw_command_output = connection.send_command(command, delay_factor=2, read_timeout=600).lstrip()

#         if gv.get_raw_output():
#             filename = "{} - {}".format(device_id, command)
#             write_info_to_txt("Raw Data", filename, "{}{}".format("{}# {}\n".format(hostname, command), raw_command_output))

#         if not textfsm:
#             return hostname, raw_command_output        
#         else:
#             if device_type == "cisco_wlc":
#                 device_type = "cisco_wlc_ssh"
#             command_output = get_structured_data(raw_command_output, platform=device_type, command=command)
        
#         if type(command_output) != list:
#             raise Exception("[!] Error parsing the output")

#         if tv.command_exists(device_type, command):
#             command_output = tv.remove_textfsm_variables(command_output, device_type, command)

#     except Exception as exception:
#         if "TCP connection to device failed" in str(exception):
#             raise Exception("[!] Error connecting to the device")
#         elif "[!] Error parsing the output" in str(exception):
#             raise Exception("[!] Error parsing the output")
#         else:
#             raise Exception("[!] Error (main function)]", exception)
            
#     return hostname, command_output
   

def set_configuration(vendor, platform, device_ip, username, password, configurations):

    device_type = "{}_{}".format(vendor, platform)
    if gv.get_connection_method() == "serial":
        connection = run_serial_connection(device_type, username, password)
        device_ip = "serial connection"
    else:
        connection = run_ssh_connection(device_type, device_ip, username, password)

    if not connection.check_config_mode():
        connection.config_mode = True
    print(connection.check_config_mode())
    return None

    command_output = connection.send_config_set(configurations)
  
    return command_output

def set_configuration_from_file(vendor, platform, device_ip, username, password, configuration_file):

    device_type = "{}_{}".format(vendor, platform)
    if gv.get_connection_method() == "serial":
        connection = run_serial_connection(device_type, username, password)
        device_ip = "serial connection"
    else:
        connection = run_ssh_connection(device_type, device_ip, username, password)

    connection.enable()
    result = connection.send_config_from_file(configuration_file)
    print(connection.check_config_mode())
    return None

    print(result)

def check_device_prompt():

    serial_port = get_serial_port()
    connection = serial.Serial(
        baudrate = serial.Serial.BAUDRATES[12],
        bytesize = serial.EIGHTBITS,
        parity = serial.PARITY_NONE,
        stopbits = serial.STOPBITS_ONE,
        port = serial_port,
    )

    connection.flush()

    if not connection.isOpen():
        sys.exit()

    connection.write("\r\n\r\n")
    time.sleep(1)
    input_data = connection.read(connection.inWaiting())
    if 'Username' in input_data:
        connection.write('warpcom')
    time.sleep(1)
    input_data = connection.read(connection.inWaiting())
    if 'Password' in input_data:
        connection.write('Warpcom.2021')
    time.sleep(1)
    input_data = connection.read(connection.inWaiting())
#    print(input_data)
