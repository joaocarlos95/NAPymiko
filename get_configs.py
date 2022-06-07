#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from networkautomation.getconfigurations import (
    get_cdp_neighbors,
    get_commands,
    get_device_configuration,
    get_device_info,
    get_device_inventory,
    get_lldp_neighbors,
    get_interfaces_info,
    get_interfaces_stats
)
from networkautomation.common.input_output_files import (
    get_set_configs_information,
    write_info_to_csv
)
from networkautomation.global_variables import global_variables as gv

FUNCTIONS = {
    "Neighbors (CDP)": get_cdp_neighbors.init,
    "Neighbors (LLDP)": get_lldp_neighbors.init,
    "Device Configuration": get_device_configuration.init,
    "Device Information": get_device_info.init,
    "Interfaces Information": get_interfaces_info.init,
    "Interfaces Statistics": get_interfaces_stats.init,
    "Device Inventory": get_device_inventory.init,
    "Custom Commands": get_commands.init,
}


if __name__ == "__main__":

    with open("get_information.txt", "r", encoding='utf-8') as file:     

        file = get_set_configs_information(file)
        for line in file:
            if ("[X]" or "[x]") in line:
                information_requested = line.split("[X] ")[1].rstrip()
                script_report = FUNCTIONS[information_requested]()

                script_report_filename = "{} - Script Report".format(information_requested)
                write_info_to_csv("..", script_report_filename, script_report)