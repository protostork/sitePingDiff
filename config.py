#!/usr/bin/python3
'''
import json

with open('config.json') as json_data_file:
    data = json.load(json_data_file)
print(data)'''

import yaml
# from pprint import pprint

def yamlCfg(configfile):
    with open(configfile, 'r') as ymlfile:
        fileString = ymlfile.read().replace('\t', '  ') # in case some tabs have crept into yaml file, convert to spaces
        cfg = yaml.load(fileString, Loader=yaml.FullLoader)
        return cfg

