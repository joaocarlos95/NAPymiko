import json
import requests

device = {
    'ip_address': '192.168.1.1',
    'port': '443',
    'username': 'cisco',
    'password': 'cisco'
}

headers = {
    'Accept': 'application/yang-data+json',
    'Content-Type': 'application/yang-data+json',
}



def get_capabilities():

    # Return all YANG data model that exists in the device
    url = f"https://{device['ip_address']}:{device['port']}/restconf/data/netconf-state/capabilities/"
    response = requests.get(url=url, headers=headers, auth=(device['username'], device['password']), verify=False)

    if response.status_code == 200:
        response_dict = response.json()
        for capability in response_dict['ietf-netconf-monitoring:capabilities']['capability']:
            print(capability)


def get_config():

    # Get routing table in a json format
    url = f"https://{device['ip_address']}:{device['port']}/restconf/data/ietf-routing/routing/"
    response = requests.get(url=url, headers=headers, auth=(device['username'], device['password']), verify=False).json()
    print(json.dumps(response, indent=2))

    # Get every interface statistics
    interface = 'GigabitEthernet1/0/1'
    url = f"https://{device['ip_address']}:{device['port']}/restconf/data/Cisco-IOS-XE-interfaces-oper:interfaces/"
    response = requests.get(url=url, headers=headers, auth=(device['username'], device['password']), verify=False).json()
    print(json.dumps(response, indent=2))

    # Get specific interface statistics
    interface = 'GigabitEthernet1/0/1'
    url = f"https://{device['ip_address']}:{device['port']}/restconf/data/Cisco-IOS-XE-interfaces-oper:interfaces/interface={interface}"
    response = requests.get(url=url, headers=headers, auth=(device['username'], device['password']), verify=False).json()
    print(json.dumps(response, indent=2))



def set_config():

    # Create new loopback interface
    url = f"https://{device['ip_address']}:{device['port']}/restconf/data/ietf-interfaces/interfaces/"
    
    # JSON
    payload = {
        'ietf-interfaces:interface': {
            'name': 'Loopback0',
            'description': "Let's rock!!!",
            'type': 'iana-if-type:softwareLoopback',
            'enabled': True,
            'ietf-ip:ipv4': {
                'address': [
                    {
                        'ip': '1.1.1.1',
                        'netmask': '255.255.255.0'
                    }
                ]
            }
        }
    }

    # Add new interface to device
    response = requests.post(url=url, headers=headers, auth=(device['username'], device['password']), data=json.dumps(payload), verify=False).json()
    if response.status.code == 201:
        print(response.text)

    # Delete interface to device. 204 code is no content
    interface = 'Loopback0'
    url = f"https://{device['ip_address']}:{device['port']}/restconf/data/ietf-interfaces/interfaces/interface=interface={interface}"
    response = requests.delete(url=url, headers=headers, auth=(device['username'], device['password']), verify=False).json()
    if response.status.code == 204:
        print(response.text)