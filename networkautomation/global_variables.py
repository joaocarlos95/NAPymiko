#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
from os.path import exists

class GlobalVariables:

    # VARIABLES
    def __init__(self):
        self.root_directory = None
        self.client = {
            "name": None,
            "directory": None
        }
        self.device_list = {
            "filename": None,
            "directory": None,
            "pathname": None
        }
        self.keepass_db = {
            "to_use": False,
            "filename": None,
            "directory": None,
            "pathname": None,
            "password": None
        }
        self.output = {
            "output_directory": None,
            "raw_output": True,
            "raw_output_directory": None
        }
        self.custom_commands = {
            "to_use": False,
            "filename": None,
            "directory": None,
            "pathname": None
        }
        self.connection_method = {
            "method": None
        }
        self.configuration_file = {
            "filename": None,
            "directory": None,
            "pathname": None
        }

    # FUNCTIONS
    def set_root_directory(self, root_directory): self.root_directory = root_directory
    def get_root_directory(self): return self.root_directory

    def set_client(self, name):
        self.client["name"] = name
        self.client["directory"] = "{}/{}/04. Automation".format(self.root_directory, name)
        os.makedirs(self.client["directory"], exist_ok=True)
        self.set_output_directory()  
    def get_client_name(self): return self.client["name"]
    def get_client_directory(self): return self.client["directory"]

    def set_device_list(self, filename):
        self.device_list["filename"] = filename
        if exists("{}/{}".format(self.client["directory"], self.device_list["filename"])):
            # Use device_list.csv from Root Directory/Client/04. Automation
            self.device_list["directory"] = self.client["directory"]
        else:
            # Use device_list.csv from source code
            self.device_list["directory"] = "."
        self.device_list["pathname"] = "{}/{}".format(self.device_list["directory"], self.device_list["filename"])
    def get_device_list_filename(self): return self.device_list["filename"]
    def get_device_list_directory(self): return self.device_list["directory"]
    def get_device_list_pathname(self): return self.device_list["pathname"]

    def set_keepass_directory(self, directory): self.keepass_db["directory"] = directory
    def set_keepass_filename(self, filename, password):
        self.keepass_db["to_use"] = True
        self.keepass_db["filename"] = filename
        self.keepass_db["pathname"] = "{}/{}".format(self.keepass_db["directory"], self.keepass_db["filename"])
        self.keepass_db["password"] = password
    def get_keepass_to_use(self): return self.keepass_db["to_use"]
    def get_keepass_filename(self): return self.keepass_db["filename"]
    def get_keepass_directory(self): return self.keepass_db["directory"]
    def get_keepass_pathname(self): return self.keepass_db["pathname"]
    def get_keepass_password(self): return self.keepass_db["password"]

    def set_raw_output(self, to_save): self.output["raw_output"] = to_save   
    def set_output_directory(self):
        self.output["output_directory"] = "{}/{}/04. Automation/Script Results".format(self.root_directory, self.client["name"])
        os.makedirs(self.output["output_directory"], exist_ok=True)
        self.output["raw_output_directory"] = "{}/{}/04. Automation/Script Results/Raw Data".format(self.root_directory, self.client["name"])
        os.makedirs(self.output["raw_output_directory"], exist_ok=True)
    def get_output_directory(self): return self.output["output_directory"]
    def get_raw_output(self): return self.output["raw_output"]
    def get_raw_output_directory(self): return self.output["raw_output_directory"]

    def set_command_list(self, filename):
        self.custom_commands["to_use"] = True
        self.custom_commands["filename"] = filename
        if exists("{}/{}".format(self.client["directory"], self.custom_commands["filename"])):
            # Use command_list.txt from Root Directory/Client/04. Automation
            self.custom_commands["directory"] = self.client["directory"]
        else:
            # Use command_list.csv from source code
            self.custom_commands["directory"] = "."
        self.custom_commands["pathname"] = "{}/{}".format(self.custom_commands["directory"], self.custom_commands["filename"])
    def get_command_list_to_use(self): return self.custom_commands["to_use"]
    def get_command_list_filename(self): return self.custom_commands["filename"]
    def get_command_list_directory(self): return self.custom_commands["directory"]
    def get_command_list_pathname(self): return self.custom_commands["pathname"]

    def set_connection_method(self, method):
        if method.lower() in ["serial", "telnet", "ssh"]:
            self.connection_method["method"] = method.lower()
    def get_connection_method(self): return self.connection_method["method"]

    def set_configuration_filename(self, filename):
        self.configuration_file["filename"] = filename
        if exists("{}/{}".format(self.client["directory"], self.configuration_file["filename"])):
            # Use command_list.txt from Root Directory/Client/04. Automation
            self.configuration_file["directory"] = self.client["directory"]
        else:
            # Use command_list.csv from source code
            self.configuration_file["directory"] = "."
        self.configuration_file["pathname"] = "{}/{}".format(self.configuration_file["directory"], self.configuration_file["filename"])
    def get_configuration_filename(self): return self.configuration_file["filename"]
    def get_configuration_directory(self): return self.configuration_file["directory"]
    def get_configuration_pathname(self): return self.configuration_file["pathname"]

global_variables = GlobalVariables()