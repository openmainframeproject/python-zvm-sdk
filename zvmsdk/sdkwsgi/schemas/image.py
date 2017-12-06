# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from zvmsdk.sdkwsgi.validation import parameter_types


create = {
    'type': 'object',
    'properties': {
        'image': {
            'type': 'object',
            'properties': {
                'image_name': parameter_types.name,
                'url': parameter_types.url,
                'image_meta': parameter_types.image_meta,
                'remote_host': parameter_types.remotehost
            },
            'required': ['image_name', 'url', 'image_meta'],
            'additionalProperties': False
        },
        'additionalProperties': False
    },
    'required': ['image'],
    'additionalProperties': False
}


export = {
    'type': 'object',
    'properties': {
        'location': {
            'type': 'object',
            'properties': {
                'dest_url': parameter_types.url,
                'remote_host': parameter_types.remotehost
            },
            'required': ['dest_url'],
            'additionalProperties': False
        },
        'additionalProperties': False
    },
    'required': ['location'],
    'additionalProperties': False
}


query = {
    'type': 'object',
    'properties': {
        'image_name': parameter_types.single_param(parameter_types.name),
        'userid': {
        'type': 'list',
        'properties': {
            'userid': parameter_types.userid_list
            },
            'additionalProperties': False
        },
        'additionalProperties': False
    },
    'required': ['image_name'],
    'additionalProperties': False
}
