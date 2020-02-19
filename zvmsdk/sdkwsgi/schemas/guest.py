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

from zvmsdk.sdkwsgi.validation import parameter_types


create = {
    'type': 'object',
    'properties': {
        'guest': {
            'type': 'object',
            'properties': {
                'userid': parameter_types.userid,
                'vcpus': parameter_types.positive_integer,
                'memory': parameter_types.positive_integer,
                # profile is similar to userid
                'user_profile': parameter_types.userid,
                'disk_list': parameter_types.disk_list,
                'max_cpu': parameter_types.max_cpu,
                'max_mem': parameter_types.max_mem,
                'ipl_from': parameter_types.ipl_from,
                'ipl_param': parameter_types.ipl_param,
                'ipl_loadparam': parameter_types.ipl_loadparam,
                'dedicate_vdevs': parameter_types.vdev_list,
                'loaddev': parameter_types.loaddev
            },
            'required': ['userid', 'vcpus', 'memory'],
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['guest'],
    'additionalProperties': False,
}

live_migrate_vm = {
    'type': 'object',
    'properties': {
        'dest_zcc_userid': parameter_types.userid,
        'destination': parameter_types.userid,
        'parms': parameter_types.live_migrate_parms,
        'operation': parameter_types.name,
    },
    'required': ['destination', 'operation'],
    'additionalProperties': False,
}

create_nic = {
    'type': 'object',
    'properties': {
        'nic': {
            'type': 'object',
            'properties': {
                'vdev': parameter_types.vdev,
                'nic_id': parameter_types.nic_id,
                'mac_addr': parameter_types.mac_address,
                'active': parameter_types.boolean,
            },
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['nic'],
    'additionalProperties': False,
}


create_network_interface = {
    'type': 'object',
    'properties': {
        'interface': {
            'type': 'object',
            'properties': {
                'os_version': parameter_types.os_version,
                'guest_networks': parameter_types.network_list,
                'active': parameter_types.boolean,
            },
            'required': ['os_version', 'guest_networks'],
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['interface'],
    'additionalProperties': False,
}


delete_network_interface = {
    'type': 'object',
    'properties': {
        'interface': {
            'type': 'object',
            'properties': {
                'os_version': parameter_types.os_version,
                'vdev': parameter_types.vdev,
                'active': parameter_types.boolean,
            },
            'required': ['os_version', 'vdev'],
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['interface'],
    'additionalProperties': False,
}


config_minidisks = {
    'type': 'object',
    'properties': {
        'disk_info': {
            'type': 'object',
            'properties': {
                'disk_list': parameter_types.disk_conf,
            },
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['disk_info'],
    'additionalProperties': False,
}


create_disks = {
    'type': 'object',
    'properties': {
        'disk_info': {
            'type': 'object',
            'properties': {
                'disk_list': parameter_types.disk_list,
            },
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['disk_info'],
    'additionalProperties': False,
}


delete_disks = {
    'type': 'object',
    'properties': {
        'vdev_info': {
            'type': 'object',
            'properties': {
                'vdev_list': parameter_types.vdev_list,
            },
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['vdev_info'],
    'additionalProperties': False,
}


nic_couple_uncouple = {
    'type': 'object',
    'properties': {
        'info': {
            'type': 'object',
            'properties': {
                'couple': parameter_types.boolean,
                'active': parameter_types.boolean,
                'vswitch': parameter_types.vswitch_name,
            },
            # FIXME: vswitch should be required when it's couple
            'required': ['couple'],
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'required': ['info'],
    'additionalProperties': False,
}


deploy = {
    'type': 'object',
    'properties': {
        'image': parameter_types.name,
        'transportfiles': {'type': ['string']},
        'remotehost': parameter_types.remotehost,
        'vdev': parameter_types.vdev,
        'hostname': parameter_types.hostname,
    },
    'required': ['image'],
    'additionalProperties': False,
}

send = {
    'type': 'object',
    'properties': {
        'transportfiles': {'type': ['string']},
        'remotehost': parameter_types.remotehost,
        'configparms': parameter_types.config_parms,
        'executeimmediate': parameter_types.boolean
    },
    'required': ['transportfiles'],
    'additionalProperties': False,
}

capture = {
    'type': 'object',
    'properties': {
        'image': parameter_types.name,
        'capture_type': parameter_types.capture_type,
        'compress_level': parameter_types.compress_level,
    },
    'required': ['image'],
    'additionalProperties': False,
}


resize_cpus = {
    'type': 'object',
    'properties': {
        'cpu_cnt': parameter_types.max_cpu,
    },
    'required': ['cpu_cnt'],
    'additionalProperties': False,
}


resize_mem = {
    'type': 'object',
    'properties': {
        'size': parameter_types.max_mem,
    },
    'required': ['size'],
    'additionalProperties': False,
}


userid_list_query = {
    'type': 'object',
    'properties': {
        'userid': parameter_types.userid_list,
    },
    'additionalProperties': False
}

register_vm = {
    'type': 'object',
    'properties': {
        'meta': {'type': ['string']},
        'net_set': {'type': ['string']},
    },
    'required': ['meta', 'net_set'],
    'additionalProperties': False
}

userid_list_array_query = {
    'type': 'object',
    'properties': {
        'userid': parameter_types.userid_list_array,
    },
    'additionalProperties': False
}

nic_DB_info = {
    'type': 'object',
    'properties': {
        'userid': parameter_types.userid,
        'nic_id': parameter_types.nic_id,
        'vswitch': parameter_types.vswitch_name,
    },
    'additionalProperties': False,
}


stop = {
    'type': 'object',
    'properties': {
        'userid': parameter_types.userid,
        'timeout': parameter_types.positive_integer,
        'poll_interval': parameter_types.positive_integer,
    },
    'additionalProperties': False,
}

softstop = {
    'type': 'object',
    'properties': {
        'userid': parameter_types.userid,
        'timeout': parameter_types.non_negative_integer,
        'poll_interval': parameter_types.non_negative_integer,
    },
    'additionalProperties': False,
}
