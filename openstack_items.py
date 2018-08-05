import os_client_config
import csv

LIMIT = 1000

def get_raw_client(cloud_name='mycloud', openstack_service_type='compute'):
    config = os_client_config.OpenStackConfig()
    cloud = config.get_one_cloud(cloud_name)
    adapter = cloud.get_session_client(openstack_service_type)
    return adapter

class novaClient:
  def __init__(self,cloud_name='mycloud'):
    self.adapter = get_raw_client()

  def get_ids(self, server_list):
    id_list = []
    for server_dict in server_list:
      id_list.append(server_dict['id'])
    return id_list

  def get_instances_detailed(self):
    uri_string = '/servers/detail?all_tenants=True&limit={limit}'.format(limit=LIMIT)
    server_list = self.adapter.get(uri_string).json()['servers']
    marker = server_list[-1]['id']
    
    while True:
      uri_string = '/servers/detail?all_tenants=True&marker=%s' % (marker)
      server_slice = self.adapter.get(uri_string).json()['servers']
      if server_slice == []:
        break
      marker = server_slice[-1]['id']
      server_list.extend(server_slice)
    return server_list
  
  def get_instance_ids(self):
    server_list = self.adapter.get('/servers?all_tenants=True&limit=%d' % LIMIT).json()['servers']
    server_id_list = self.get_ids(server_list)
    marker = server_list[-1]['id']
    
    while True:
      uri_string = '/servers?all_tenants=True&marker=%s' % (marker)
      server_slice = self.adapter.get(uri_string).json()['servers']
      if server_slice == []:
        break
      marker = server_slice[-1]['id']
      server_id_list.extend(self.get_ids(server_slice))
    return server_id_list
  
  def get_instance_volumes(self, instance_id):
    uri_string = '/servers/{instance_id}/os-volume_attachments'.format(instance_id=instance_id)
    volume_ids = self.get_ids(self.adapter.get(uri_string).json()['volumeAttachments'])
    return volume_ids

  def get_instance_volumes_from_metadata(self, metadata):
    volume_ids = self.get_ids(metadata['os-extended-volumes:volumes_attached'])
    return volume_ids

  def get_instance_hypervisor_from_metadata(self, metadata):
    hypervisor = metadata['OS-EXT-SRV-ATTR:hypervisor_hostname']
    return hypervisor

  def get_instance_metadata(self, instance_id):
    uri_string = '/servers/{instance_id}'.format(instance_id=instance_id)
    metadata = self.adapter.get(uri_string).json()['server']
    return metadata

  def get_instance_hypervisor(self, instance_id):
    uri_string = '/servers/{instance_id}'.format(instance_id=instance_id)
    hypervisor = self.adapter.get(uri_string).json()['server']['OS-EXT-SRV-ATTR:hypervisor_hostname']
    return hypervisor

  def windows_hosts(self, aggregate='341'):
   uri_string = '/os-aggregates/{aggregate_id}'.format(aggregate_id=aggregate)
   return self.adapter.get(uri_string).json()['aggregate']['hosts']

class cinderClient:
  def __init__(self):
    self.adapter = get_raw_client(openstack_service_type='volume')

  def get_volume_source_image(self, volume_id):
    uri_string = '/volumes/{volume_id}'.format(volume_id=volume_id)
    image_key = 'volume_image_metadata'
    try:
      volume_detail = self.adapter.get(uri_string).json()['volume']
    except:
      return None
    return volume_detail['volume_image_metadata']['image_id'] if image_key in volume_detail.keys() else None
    
class glanceClient:

  def __init__(self):
    self.adapter = get_raw_client(openstack_service_type='image')
     
  def get_windows_images(self):
    uri_string = '/v2/images?os_type=windows'
    image_list = self.adapter.get(uri_string).json()['images']
    windows_images = []
    for image in image_list:
      windows_images.append(image['id'])
    return windows_images

def is_windows_by_id(instance_id):
  nova_client = novaClient()
  cinder_client = cinderClient()
  glance_client = glanceClient()

  windows_images = glance_client.get_windows_images()
  volume_ids = nova_client.get_instance_volumes(instance_id)

  for volume_id in volume_ids:
    image = cinder_client.get_volume_source_image(volume_id)
    if image in windows_images:
      return True
    else: 
      return False

def is_windows_by_dict(instance_dict):
  nova_client = novaClient()
  cinder_client = cinderClient()
  glance_client = glanceClient()

  windows_images = glance_client.get_windows_images()
  volume_ids = nova_client.get_instance_volumes_from_metadata(instance_dict)

  for volume_id in volume_ids:
    image = cinder_client.get_volume_source_image(volume_id)
    if image in windows_images:
      return True
    else: 
      return False

def get_miration_list(instance_list):
  nova_client = novaClient()
  windows_hosts = nova_client.windows_hosts()
  migration_list = []
  for instance_details in instance_list:
    instance_dict = {}
    if nova_client.get_instance_hypervisor_from_metadata(instance_details) in windows_hosts:
      instance_dict['aggregate_os_type'] = 'windows'
    else:
      instance_dict['aggregate_os_type'] = 'rest'
    if is_windows_by_dict(instance_details):
      instance_dict['instance_os_type'] = 'windows'
    else:
      instance_dict['instance_os_type'] = 'rest'
    if instance_dict['instance_os_type'] != instance_dict['aggregate_os_type']:
      instance_dict["instance_id"] = instance_details["id"]
      migration_list.append(instance_dict)
    print('instance_type is: {os_type}, aggregate_type is: {aggr_type}'.format(os_type=instance_dict['instance_os_type'], aggr_type=instance_dict['aggregate_os_type']))
  return migration_list

  
nova_client = novaClient()
instances = nova_client.get_instances_detailed()

my_list = get_miration_list(instances)

with open('mycsvfile.csv', 'wb') as f:
    w = csv.DictWriter(f, my_list[0].keys())
    w.writeheader()
    for my_dict in my_list:
        w.writerow(my_dict)

