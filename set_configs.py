#!/usr/bin/env python
# -*- coding: UTF-8 -*-


from networkautomation.common.input_output_files import (
    get_set_configs_information,
    write_info_to_csv
)
from networkautomation.common.main import (
    check_device_prompt,
    set_configuration,
    set_configuration_from_file
)
from networkautomation.global_variables import global_variables as gv


import yaml
from jinja2 import Environment, FileSystemLoader


if __name__ == "__main__":

    with open("set_information.txt", "r", encoding='utf-8') as file:     

        file = get_set_configs_information(file)
        for line in file:

            if ("[X]" or "[x]") in line:
                information_requested = line.split("[X] ")[1].rstrip()
                script_report = None

                script_report_filename = "{} - Script Report".format(information_requested)
                write_info_to_csv("..", script_report_filename, script_report)

        #with open(gv.get_configuration_pathname()) as configuration_file: configuration = configuration_file.read()
        check_device_prompt()
        #set_configuration_from_file("cisco", "ios", None, None, None, gv.get_configuration_pathname())

        '''
        loader = FileSystemLoader([
            "networkautomation/setconfigurations/jinja2_templates",
            global_variables.CLIENT_DIRECTORY
        ])
        environment = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)

        j2_template = environment.get_template("configuration.j2")
        yaml_config = yaml.full_load(open("{}/{}".format(global_variables.CLIENT_DIRECTORY, "master_config.yaml")))

        configuration = j2_template.render(yaml_config, ip_address=ip_address)

        print(configuration)

        '''
        
