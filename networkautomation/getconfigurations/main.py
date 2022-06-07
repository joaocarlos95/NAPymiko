#!/usr/bin/env python
# -*- coding: UTF-8 -*-


def get_stack_info(output_to_parse):
    
    is_stack, stack_length = get_stack_len(output_to_parse)
    if is_stack:
        command_output = []
        for i in range(0, stack_length):
            command_output_aux = output_to_parse.copy()

            for key, value in command_output_aux.items():
                if type(value) == list:
                    command_output_aux[key] = value[i-1]
            
            command_output.append(command_output_aux)
    else:
        command_output = [{key: "".join(value) for key, value in output_to_parse.items()}]
    
    return command_output


def get_stack_len(output_to_parse):

    for value in output_to_parse.values():
        if type(value) == list and len(value) > 1:
            return True, len(value)

    return False, None