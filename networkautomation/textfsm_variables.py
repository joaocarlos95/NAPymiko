
class TextfsmVariables:

    # VARIABLES
    def __init__(self):
        self.textfsm_variables = {
            "cisco_ios": {
                "show interfaces status": {
                    "port": "interface_name",
                    "status": "interface_status",
                    "vlan": "vlan",
                    "duplex": "interface_duplex",
                    "speed": "interface_speed"
                },
                "show power inline": {
                    "interface": "interface_name",
                    "oper": "poe_status",
                    "power": "poe_power",
                    "class": "poe_class",
                    "max": "poe_max"
                },
                "show interfaces description":  {
                    "port": "interface_name",
                    "descrip": "interface_description"
                },
                "show interfaces switchport": {
                    "interface": "interface_name",
                    "mode": "switchport_mode",
                    "admin_mode": "switchport_admin_mode",
                    "voice_vlan": "voice_vlan",
                    "native_vlan": "native_vlan",
                    "access_vlan": "access_vlan",
                    "trunking_vlans": "trunk_vlans"
                },
                "show interfaces": {
                    "interface": "interface_name",
                    "link_status": "link_status",
                    "protocol_status": "protocol_Status",
                    "hardware_type": "hardware_type",
                    "address": "address",
                    "bia": "bia",
                    "description": "description",
                    "ip_address": "ip_address",
                    "mtu": "mtu",
                    "duplex": "duplex",
                    "speed": "speed",
                    "media_type": "media_type",
                    "bandwidth": "bandwidth",
                    "delay": "delay",
                    "encapsulation": "encapsulation",
                    "reliability": "reliability",
                    "rx_load": "rx_load",
                    "tx_load": "tx_load",
                    "last_input": "last_input",
                    "last_output": "last_output",
                    "last_output_hang": "last_output_hang",
                    "queue_strategy": "queue_strategy",
                    "input_rate": "input_rate",
                    "output_rate": "output_rate",
                    "input_errors": "input_errors",
                    "crc": "crc",
                    "abort": "abort",
                    "output_errors": "output_errors",
                },
                "show version": {
                    "hardware": "model",
                    "serial": "serial_number",
                    "version": "version",
                    "hostname": "hostname",
                    "uptime": "system_uptime",
                    "mac": "mac_address",
                },
                "show inventory": {
                    "pid": "product_id",
                    "sn": "serial_number",
                    "name": "additional_info",
                },
                "show cdp neighbors detail": {
                    "destination_host": "neighbor_hostname",
                    "management_ip": "neighbor_ip",
                    "platform": "neighbor_model",
                    "remote_port": "neighbor_interface",
                    "local_port": "local_interface",
                },
                "show lldp neighbors detail": {
#                    "neighbor": "neighbor_hostname",
#                    "local_interface": "local_interface",
#                    "neighbor_port_id": "neighbor_interface",
                    "management_ip": "neighbor_ip",
                },
                "show lldp neighbors": {
                    "neighbor": "neighbor_hostname",
                    "local_interface": "local_interface",
                    "neighbor_interface": "neighbor_interface"
                },
            }
        }

    # FUNCTIONS
    def remove_textfsm_variables(self, command_output, device_type, command):

        command_output_aux = []
        for element in command_output:

            element_aux = {}
            for key, value in element.items():

                if key in self.textfsm_variables[device_type][command]:
                    element_aux[self.textfsm_variables[device_type][command][key]] = value

            command_output_aux.append(element_aux)
                        
        return command_output_aux
    
    def command_exists(self, device_type, command):
        return command in self.textfsm_variables[device_type]


textfsm_variables = TextfsmVariables()