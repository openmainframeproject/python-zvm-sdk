# Copyright 2017,2018 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

HYPERVISOR_TYPE = 'zvm'
ARCHITECTURE = 's390x'
ALLOWED_VM_TYPE = 'zLinux'
PROV_METHOD = 'netboot'
ZVM_USER_DEFAULT_PRIVILEGE = 'G'
CONFIG_DRIVE_FORMAT = 'tgz'
DEFAULT_EPH_DISK_FMT = 'ext3'
DISK_FUNC_NAME = 'setupDisk'

RINV_HOST_KEYWORDS = {
    "zcc_userid": "ZCC USERID:",
    "zvm_host": "z/VM Host:",
    "zhcp": "zHCP:",
    "cec_vendor": "CEC Vendor:",
    "cec_model": "CEC Model:",
    "hypervisor_os": "Hypervisor OS:",
    "hypervisor_name": "Hypervisor Name:",
    "architecture": "Architecture:",
    "lpar_cpu_total": "LPAR CPU Total:",
    "lpar_cpu_used": "LPAR CPU Used:",
    "lpar_memory_total": "LPAR Memory Total:",
    "lpar_memory_used": "LPAR Memory Used:",
    "lpar_memory_offline": "LPAR Memory Offline:",
    "ipl_time": "IPL Time:",
    }

DISKPOOL_KEYWORDS = {
    "disk_total": "Total:",
    "disk_used": "Used:",
    "disk_available": "Free:",
    }

SET_VSWITCH_KEYWORDS = ["grant_userid", "user_vlan_id",
                        "revoke_userid", "real_device_address",
                        "port_name", "controller_name",
                        "connection_value", "queue_memory_limit",
                        "routing_value", "port_type", "persist",
                        "gvrp_value", "mac_id", "uplink",
                        "nic_userid", "nic_vdev",
                        "lacp", "interval", "group_rdev",
                        "iptimeout", "port_isolation", "promiscuous",
                        "MAC_protect", "VLAN_counters"]

DEV_STATUS = {'0': 'Device is not active.',
              '1': 'Device is active.',
              '2': 'Device is a backup device'}

DEV_ERROR = {'0': 'No error.',
             '1': 'Port name conflict.',
             '2': 'No layer 2 support.',
             '3': 'Real device does not exist.',
             '4': 'Real device is attached elsewhere.',
             '5': 'Real device is not compatible type.',
             '6': 'Initialization error.',
             '7': 'Stalled OSA.',
             '8': 'Stalled controller.',
             '9': 'Controller connection severed.',
             '10': 'Primary or secondary routing conflict.',
             '11': 'Device is offline.',
             '12': 'Device was detached.',
             '13': 'IP/Ethernet type mismatch.',
             '14': 'Insufficient memory in controller '
                   'virtual machine.',
             '15': 'TCP/IP configuration conflict.',
             '16': 'No link aggregation support.',
             '17': 'OSA-E attribute mismatch.',
             '18': 'Reserved for future use.',
             '19': 'OSA-E is not ready.',
             '20': 'Reserved for future use.',
             '21': 'Attempting restart for device.',
             '22': 'Exclusive user error.',
             '23': 'Device state is invalid.',
             '24': 'Port number is invalid for device.',
             '25': 'No OSA connection isolation.',
             '26': 'EQID mismatch.',
             '27': 'Incompatible controller.',
             '28': 'BACKUP detached.',
             '29': 'BACKUP not ready.',
             '30': 'BACKUP attempting restart.',
             '31': 'EQID mismatch.',
             '32': 'No HiperSockets bridge support.',
             '33': 'HiperSockets bridge error.'}

SWITCH_STATUS = {'1': 'Virtual switch defined.',
                 '2': 'Controller not available.',
                 '3': 'Operator intervention required.',
                 '4': 'Disconnected.',
                 '5': 'Virtual devices attached to controller. '
                      'Normally a transient state.',
                 '6': 'OSA initialization in progress. '
                      'Normally a transient state.',
                 '7': 'OSA device not ready',
                 '8': 'OSA device ready.',
                 '9': 'OSA devices being detached. '
                      'Normally a transient state.',
                 '10': 'Virtual switch delete pending. '
                       'Normally a transient state.',
                 '11': 'Virtual switch failover recovering. '
                       'Normally a transient state.',
                 '12': 'Autorestart in progress. '
                       'Normally a transient state.'}

ZVM_VOLUMES_FILE = 'zvm_volumes'
ZVM_VOLUME_STATUS = ['free', 'in-use']
VOLUME_MULTI_PASS = 'MULTI'

POWER_STATE_ON = u'on'
POWER_STATE_OFF = u'off'

DATABASE_VOLUME = 'sdk_volume.sqlite'
DATABASE_NETWORK = 'sdk_network.sqlite'
DATABASE_GUEST = 'sdk_guest.sqlite'
DATABASE_IMAGE = 'sdk_image.sqlite'
DATABASE_FLASHIMAGE = 'sdk_flashimage.sqlite'
DATABASE_FCP = 'sdk_fcp.sqlite'

IMAGE_TYPE = {
    'DEPLOY': 'netboot',
    'CAPTURE': 'staging'}

FILE_TYPE = {
    'IMPORT': 'imported',
    'EXPORT': 'exported'}

SDK_DATA_PATH = '/var/lib/zvmsdk/'
