from netmiko import ConnectHandler

device = {
    'ip_address': '192.168.1.1',
    'port': '22',
    'username': 'cisco',
    'password': 'cisco',
    'device_type': 'cisco_ios'
}



def get_config():

    try:
        c = ConnectHandler(**device)
        c.enable()
        response = c.send_command('show running-config')
        c.disconnect()

    except Exception as ex:
        print(ex)
    else:
        print(response)



def get_config_textfsm():

    try:
        c = ConnectHandler(**device)
        c.enable()
        response = c.send_command('show running-config', use_textfsm=True)
        c.disconnect()

    except Exception as ex:
        print(ex)
    else:
        print(response)



def set_config():

    configs = ['interface loopback101', 'ip address 1.1.1.1 255.255.255.0', 'no shutdown']

    try:
        c = ConnectHandler(**device)
        c.enable()
        # Send config via list (configs variable)
        c.send_config_set(configs)
        # Send config via text file
        c.send_config_from_file('./config_example.txt')
        # Confirm that the new loopback interface was created
        response = c.send_command('show ip interface bried', use_textfsm=True)
        c.disconnect()

    except Exception as ex:
        print(ex)
    else:
        print(response)