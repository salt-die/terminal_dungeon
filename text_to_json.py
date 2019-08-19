#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"Helper function to convert textures and maps to json"
import json

def text_to_json(filename):
    with open(filename + ".txt", "r") as text:
        pre_format = [list(row) for row in text.read().splitlines()]
        jsontext = json.dumps(pre_format)

    with open(filename + ".json", "w") as new_file:
        new_file.write(jsontext)
