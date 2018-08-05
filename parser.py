#!/usr/bin/env python

import json, sys
import argparse

target_map = {
  "volumes": "get_volume_ids",
  "hypervisor": "get_hypervisor"  
}

json_map = {
  "volumes": "os-extended-volumes:volumes_attached",
  "hypervisor": "OS-EXT-SRV-ATTR:hypervisor_hostname"
}

def parse_arguments():

  parser = argparse.ArgumentParser(description='basic json parser')
  parser.add_argument('-t', '--target',
                      help='enter what is needed to be extracted from provided json',
                      required=True,
                      dest='target')
  parser.add_argument('--json', 
                      help='json string to be parsed',
                      required=True,
                      dest='json_raw')
  args = parser.parse_args()

  json_string = json.loads(args.json_raw)
  return args.target, json_string

class jsonAction:
  def get_volume_ids(self, json_object):
    id_list = []
    for dictionary in json_object[json_map["volumes"]]:
      id_list.append(dictionary["id"])
    return id_list

  def get_hypervisor(self, json_object):
    hypervisor_name = json_object[json_map["hypervisor"]]
    return hypervisor_name

def main():
  args_tuple = parse_arguments()
  actions_obj = jsonAction()
  action = getattr(actions_obj, target_map[args_tuple[0]])
  json_obj = args_tuple[1]
  result = { args_tuple[0]: action(json_obj) }
  print(result)

if __name__== "__main__":
  sys.exit(main())
