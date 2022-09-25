from ncclient import manager
import xmltodict

device = {
    'ip_address': '192.168.1.1',
    'port': '22',
    'username': 'cisco',
    'password': 'cisco'
}



def get_capabilities():

    # Return all YANG data model that exists in the device
    with manager.connect(**device, hostkey_verify=False) as m:
        for capability in m.server_capabilities:
            print(capability)



def get_config():

    # Filter to get two informations (two ):
    #   1) Interface configuration
    #   2) Interface operational state
    int_filter = """
        <filter>
            <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
                <interface>
                    <name>GigabitEthernet2</name>
                </interface>
            </interfaces
            <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
                <interface>
                    <name>GigabitEthernet2</name>
                </interface>
            </interfaces-state>
        </filter>
    """

    with manager.connect(**device, hostkey_verify=False) as m:
        netconf_response = m.get(int_filter)

    # Convert XML response to Dict4
    python_response = xmltodict.parse(netconf_response.xml)['rpc-reply']['data']

    int_state = python_response['interfaces-state']['interface']
    int_config = python_response['interfaces']['interface']

    print(f"Interface Name: {int_config['name']['#text']}")
    print(f"Packets In: {int_state['statistics']['in-unicast-pkts']}")
    print(f"Packets Out: {int_state['statistics']['outn-unicast-pkts']}")



def set_config():

    config_template = open('./ios_config.xml').read()

    netconf_config = config_template.format(
        interface_name = 'GigabitEthernet1/0/1',
        interface_description = 'Uplink to Sucess',
        interface_enabled = 'true'
    )

    with manager.connect(**device, hostkey_verify=False) as m:
        response = m.edit_config(netconf_config, target='candidate')

    print(response)