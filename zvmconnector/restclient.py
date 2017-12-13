# Copyright 2017 IBM Corp.
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

import copy
import errno
import hashlib
import json
import os
import requests
import six
import threading
import logging
import urlparse

# TODO:set up configuration file only for RESTClient and configure this value
TOKEN_LOCK = threading.Lock()
CHUNKSIZE = 4096


REST_REQUEST_ERROR = [{'overallRC': 101, 'modID': 110, 'rc': 101},
                      {1: "Request to zVM Cloud Connector failed: %(error)s",
                       2: "Token file not found: %(error)s",
                       3: "Request to url: %(url)s got unexpected response: "
                       "status_code: %(status)s, reason: %(reason)s, "
                       "text: %(text)s",
                       4: "Get Token failed: %(error)s"},
                       "zVM Cloud Connector request failed",
                       ]
SERVICE_UNAVAILABLE_ERROR = [{'overallRC': 503, 'modID': 110, 'rc': 503},
                             {2: "Service is unavailable. reason: %(reason)s,"
                              " text: %(text)s"},
                             "Service is unavailable",
                             ]
INVALID_API_ERROR = [{'overallRC': 400, 'modID': 110, 'rc': 400},
                     {1: "Invalid API name, '%(msg)s'"},
                     "Invalid API name",
                     ]


class UnexpectedResponse(Exception):
    def __init__(self, resp):
        self.resp = resp


class ServiceUnavailable(Exception):
    def __init__(self, resp):
        self.resp = resp


class Logger():
    def __init__(self, logger, log_dir='/var/log/restclient',
                 log_file_name='restclient.log', level=logging.INFO):
        # make sure target directory exists
        if not os.path.exists(log_dir):
            if os.access(log_dir, os.W_OK):
                os.makedirs(log_dir)
            else:
                log_dir = '/tmp/'

        # create a logger
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(level)

        # create a handler for the file
        log_file = os.path.join(log_dir, log_file_name)
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)

        # set the format of the handler
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)

        # add handler in the logger
        self.logger.addHandler(fh)

    def getlog(self):
        return self.logger


class TokenNotFound(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class TokenFileOpenError(Exception):
    def __init__(self, msg):
        self.msg = msg


class CACertNotFound(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class APINameNotFound(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class ArgsFormatError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


def fill_kwargs_in_body(body, **kwargs):
    for key in kwargs.keys():
        body[key] = kwargs.get(key)


def req_version(start_index, *args, **kwargs):
    url = '/'
    body = None
    return url, body


def req_guest_list(start_index, *args, **kwargs):
    url = '/guests'
    body = None
    return url, body


def req_guest_delete(start_index, *args, **kwargs):
    url = '/guests/%s'
    body = None
    return url, body


def req_guest_get_definition_info(start_index, *args, **kwargs):
    url = '/guests/%s'
    body = None
    return url, body


def req_guest_create(start_index, *args, **kwargs):
    url = '/guests'
    body = {'guest': {'userid': args[start_index],
                      'vcpus': args[start_index + 1],
                      'memory': args[start_index + 2]}}
    fill_kwargs_in_body(body['guest'], **kwargs)
    return url, body


def req_guest_inspect_stats(start_index, *args, **kwargs):
    url = '/guests/stats?userid=%s'
    body = None
    return url, body


def req_guest_inspect_vnics(start_index, *args, **kwargs):
    url = '/guests/vnicsinfo?userid=%s'
    body = None
    return url, body


def req_guests_get_nic_info(start_index, *args, **kwargs):
    url = '/guests/nics'
    # process appends in GET method
    userid = kwargs.get('userid', None)
    nic_id = kwargs.get('nic_id', None)
    vswitch = kwargs.get('vswitch', None)
    if ((userid is None) and
        (nic_id is None) and
        (vswitch is None)):
            append = ''
    else:
        append = "?"
        if userid is not None:
            append += 'userid=%s&' % userid
        if nic_id is not None:
            append += 'nic_id=%s&' % nic_id
        if vswitch is not None:
            append += 'vswitch=%s&' % vswitch
        append = append.strip('&')
    url = url + append
    body = None
    return url, body


# FIXME: the order of args need adjust
def req_guest_start(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'start'}
    return url, body


def req_guest_stop(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'stop'}
    fill_kwargs_in_body(body, **kwargs)
    return url, body


def req_guest_softstop(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'softstop'}
    fill_kwargs_in_body(body, **kwargs)
    return url, body


def req_guest_pause(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'pause'}
    return url, body


def req_guest_unpause(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'unpause'}
    return url, body


def req_guest_reboot(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'reboot'}
    return url, body


def req_guest_reset(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'reset'}
    return url, body


def req_guest_get_console_output(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'get_console_output'}
    return url, body


def req_guest_capture(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'capture',
            'image': args[start_index]}
    fill_kwargs_in_body(body, **kwargs)
    return url, body


def req_guest_deploy(start_index, *args, **kwargs):
    url = '/guests/%s/action'
    body = {'action': 'deploy',
            'image': args[start_index]}
    fill_kwargs_in_body(body, **kwargs)
    return url, body


def req_guest_get_info(start_index, *args, **kwargs):
    url = '/guests/%s/info'
    body = None
    return url, body


def req_guest_get_nic_vswitch_info(start_index, *args, **kwargs):
    url = '/guests/%s/nic'
    body = None
    return url, body


def req_guest_create_nic(start_index, *args, **kwargs):
    url = '/guests/%s/nic'
    body = {'nic': {}}
    fill_kwargs_in_body(body['nic'], **kwargs)
    return url, body


def req_guest_delete_nic(start_index, *args, **kwargs):
    url = '/guests/%s/nic/%s'
    body = {}
    fill_kwargs_in_body(body, **kwargs)
    return url, body


def req_guest_nic_couple_to_vswitch(start_index, *args, **kwargs):
    url = '/guests/%s/nic/%s'
    body = {'info': {'couple': True,
                     'vswitch': args[start_index]}}
    fill_kwargs_in_body(body['info'], **kwargs)
    return url, body


def req_guest_nic_uncouple_from_vswitch(start_index, *args, **kwargs):
    url = '/guests/%s/nic/%s'
    body = {'info': {'couple': False}}
    fill_kwargs_in_body(body['info'], **kwargs)
    return url, body


def req_guest_create_network_interface(start_index, *args, **kwargs):
    url = '/guests/%s/interface'
    body = {'interface': {'os_version': args[start_index],
                          'guest_networks': args[start_index + 1]}}
    fill_kwargs_in_body(body['interface'], **kwargs)
    return url, body


def req_guest_delete_network_interface(start_index, *args, **kwargs):
    url = '/guests/%s/interface'
    body = {'interface': {'os_version': args[start_index],
                          'vdev': args[start_index + 1]}}
    fill_kwargs_in_body(body['interface'], **kwargs)
    return url, body


def req_guest_get_power_state(start_index, *args, **kwargs):
    url = '/guests/%s/power_state'
    body = None
    return url, body


def req_guest_create_disks(start_index, *args, **kwargs):
    url = '/guests/%s/disks'
    body = {'disk_info': {'disk_list': args[start_index]}}
    return url, body


def req_guest_delete_disks(start_index, *args, **kwargs):
    url = '/guests/%s/disks'
    body = {'vdev_info': {'vdev_list': args[start_index]}}
    return url, body


def req_guest_config_minidisks(start_index, *args, **kwargs):
    url = '/guests/%s/disks'
    body = {'disk_info': {'disk_list': args[start_index]}}
    fill_kwargs_in_body(body['disk_info'], **kwargs)
    return url, body


# FIXME: (userid, os_type) in one params, how to parse?
def req_volume_attach(start_index, *args, **kwargs):
    url = '/guests/%s/volumes'
    body = {'info': {'os_type': args[start_index],
                     'volume': args[start_index + 1],
                     'connection': args[start_index + 2],
                     'rollback': args[start_index + 3]}}
    fill_kwargs_in_body(body['info'], **kwargs)
    return url, body


# FIXME: (userid, os_type) in one params, how to parse?
def req_volume_detach(start_index, *args, **kwargs):
    url = '/guests/%s/volumes'
    body = {'info': {'os_type': args[start_index],
                     'volume': args[start_index + 1],
                     'connection': args[start_index + 2],
                     'rollback': args[start_index + 3]}}
    fill_kwargs_in_body(body['info'], **kwargs)
    return url, body


def req_host_get_info(start_index, *args, **kwargs):
    url = '/host'
    body = None
    return url, body


def req_host_diskpool_get_info(start_index, *args, **kwargs):
    url = '/host/diskpool'
    poolname = kwargs.get('disk_pool', None)
    append = ''
    if poolname is not None:
        append += "?poolname=%s" % poolname
    url += append
    body = None
    return url, body


def req_image_import(start_index, *args, **kwargs):
    url = '/images'
    body = {'image': {'image_name': args[start_index],
                      'url': args[start_index + 1],
                      'image_meta': args[start_index + 2]}}
    fill_kwargs_in_body(body['image'], **kwargs)
    return url, body


def req_image_query(start_index, *args, **kwargs):
    url = '/images'
    image_name = kwargs.get('imagename', None)
    if image_name is None:
        append = ''
    else:
        append = "?"
        append += "imagename=%s" % image_name
    url += append
    body = None
    return url, body


def req_image_delete(start_index, *args, **kwargs):
    url = '/images/%s'
    body = None
    return url, body


def req_image_export(start_index, *args, **kwargs):
    url = '/images/%s'
    body = {'location': {'dest_url': args[start_index]}}
    fill_kwargs_in_body(body['location'], **kwargs)
    return url, body


def req_image_get_root_disk_size(start_index, *args, **kwargs):
    url = '/images/%s/root_disk_size'
    body = None
    return url, body


def req_image_upload(start_index, *args, **kwargs):
    url = '/images/%s/file'
    image_spath = urlparse.urlparse(args[start_index]).path
    body = get_data_file(image_spath)
    return url, body


# image_download(imagename, dest_url)
def req_image_download(start_index, *args, **kwargs):
    url = '/images/%s/file'
    body = None

    return url, body


def req_token_create(start_index, *args, **kwargs):
    url = '/token'
    body = None
    return url, body


def req_vswitch_get_list(start_index, *args, **kwargs):
    url = '/vswitches'
    body = None
    return url, body


def req_vswitch_create(start_index, *args, **kwargs):
    url = '/vswitches'
    body = {'vswitch': {'name': args[start_index]}}
    fill_kwargs_in_body(body['vswitch'], **kwargs)
    return url, body


def req_vswitch_delete(start_index, *args, **kwargs):
    url = '/vswitches/%s'
    body = None
    return url, body


def req_vswitch_query(start_index, *args, **kwargs):
    url = '/vswitches/%s'
    body = None
    return url, body


def req_vswitch_grant_user(start_index, *args, **kwargs):
    url = '/vswitches/%s'
    body = {'vswitch': {'grant_userid': args[start_index]}}
    fill_kwargs_in_body(body['vswitch'], **kwargs)
    return url, body


def req_vswitch_revoke_user(start_index, *args, **kwargs):
    url = '/vswitches/%s'
    body = {'vswitch': {'revoke_userid': args[start_index]}}
    fill_kwargs_in_body(body['vswitch'], **kwargs)
    return url, body


def req_vswitch_set_vlan_id_for_user(start_index, *args, **kwargs):
    url = '/vswitches/%s'
    body = {'vswitch': {'user_vlan_id': {'userid': args[start_index],
                                         'vlanid': args[start_index + 1]}}}
    fill_kwargs_in_body(body['vswitch'], **kwargs)
    return url, body


# Save data used for comprsing RESTful request
# method: request type
# args_required: arguments in args are required, record the count here.
#                if len(args) not equal to this number, raise exception
# params_path: parameters amount in url path
# request: function that provide url and body for comprosing a request
DATABASE = {
    'version': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_version},
    'guest_create': {
        'method': 'POST',
        'args_required': 3,
        'params_path': 0,
        'request': req_guest_create},
    'guest_list': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_guest_list},
    'guest_inspect_stats': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_inspect_stats},
    'guest_inspect_vnics': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_inspect_vnics},
    'guests_get_nic_info': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_guests_get_nic_info},
    'guest_delete': {
        'method': 'DELETE',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_delete},
    'guest_get_definition_info': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_get_definition_info},
    'guest_start': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_start},
    'guest_stop': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_stop},
    'guest_softstop': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_softstop},
    'guest_pause': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_pause},
    'guest_unpause': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_unpause},
    'guest_reboot': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_reboot},
    'guest_reset': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_reset},
    'guest_get_console_output': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_get_console_output},
    'guest_capture': {
        'method': 'POST',
        'args_required': 2,
        'params_path': 1,
        'request': req_guest_capture},
    'guest_deploy': {
        'method': 'POST',
        'args_required': 2,
        'params_path': 1,
        'request': req_guest_deploy},
    'guest_get_info': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_get_info},
    'guest_get_nic_vswitch_info': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_get_nic_vswitch_info},
    'guest_create_nic': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_create_nic},
    'guest_delete_nic': {
        'method': 'DELETE',
        'args_required': 2,
        'params_path': 2,
        'request': req_guest_delete_nic},
    'guest_nic_couple_to_vswitch': {
        'method': 'PUT',
        'args_required': 3,
        'params_path': 2,
        'request': req_guest_nic_couple_to_vswitch},
    'guest_nic_uncouple_from_vswitch': {
        'method': 'PUT',
        'args_required': 2,
        'params_path': 2,
        'request': req_guest_nic_uncouple_from_vswitch},
    'guest_create_network_interface': {
        'method': 'POST',
        'args_required': 3,
        'params_path': 1,
        'request': req_guest_create_network_interface},
    'guest_delete_network_interface': {
        'method': 'DELETE',
        'args_required': 3,
        'params_path': 1,
        'request': req_guest_delete_network_interface},
    'guest_get_power_state': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_guest_get_power_state},
    'guest_create_disks': {
        'method': 'POST',
        'args_required': 2,
        'params_path': 1,
        'request': req_guest_create_disks},
    'guest_delete_disks': {
        'method': 'DELETE',
        'args_required': 2,
        'params_path': 1,
        'request': req_guest_delete_disks},
    'guest_config_minidisks': {
        'method': 'PUT',
        'args_required': 2,
        'params_path': 1,
        'request': req_guest_config_minidisks},
    'volume_attach': {
        'method': 'POST',
        'args_required': 3,
        'params_path': 1,
        'request': req_volume_attach},
    'volume_detach': {
        'method': 'DELETE',
        'args_required': 3,
        'params_path': 1,
        'request': req_volume_detach},
    'host_get_info': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_host_get_info},
    'host_diskpool_get_info': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_host_diskpool_get_info},
    'image_import': {
        'method': 'POST',
        'args_required': 3,
        'params_path': 0,
        'request': req_image_import},
    'image_query': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_image_query},
    'image_delete': {
        'method': 'DELETE',
        'args_required': 1,
        'params_path': 1,
        'request': req_image_delete},
    'image_export': {
        'method': 'PUT',
        'args_required': 2,
        'params_path': 1,
        'request': req_image_export},
    'image_get_root_disk_size': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_image_get_root_disk_size},
    'image_upload': {
        'method': 'PUT',
        'args_required': 3,
        'params_path': 1,
        'request': req_image_upload},
    'image_download': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_image_download},
    'token_create': {
        'method': 'POST',
        'args_required': 0,
        'params_path': 0,
        'request': req_token_create},
    'vswitch_get_list': {
        'method': 'GET',
        'args_required': 0,
        'params_path': 0,
        'request': req_vswitch_get_list},
    'vswitch_create': {
        'method': 'POST',
        'args_required': 1,
        'params_path': 0,
        'request': req_vswitch_create},
    'vswitch_delete': {
        'method': 'DELETE',
        'args_required': 1,
        'params_path': 1,
        'request': req_vswitch_delete},
    'vswitch_grant_user': {
        'method': 'PUT',
        'args_required': 2,
        'params_path': 1,
        'request': req_vswitch_grant_user},
    'vswitch_query': {
        'method': 'GET',
        'args_required': 1,
        'params_path': 1,
        'request': req_vswitch_query},
    'vswitch_revoke_user': {
        'method': 'PUT',
        'args_required': 2,
        'params_path': 1,
        'request': req_vswitch_revoke_user},
    'vswitch_set_vlan_id_for_user': {
        'method': 'PUT',
        'args_required': 3,
        'params_path': 1,
        'request': req_vswitch_set_vlan_id_for_user},
}


def get_data_file(fpath):
    if fpath:
        return open(fpath, 'rb')


def get_file_size(file_obj):
    """Analyze file-like object and attempt to determine its size.
    :param file_obj: file-like object.
    :retval: The file's size or None if it cannot be determined.
    """
    if (hasattr(file_obj, 'seek') and hasattr(file_obj, 'tell') and
            (six.PY2 or six.PY3 and file_obj.seekable())):
        try:
            curr = file_obj.tell()
            file_obj.seek(0, os.SEEK_END)
            size = file_obj.tell()
            file_obj.seek(curr)
            return size
        except IOError as e:
            if e.errno == errno.ESPIPE:
                msg = ('Failed to get the size of specific file object with '
                'reason: the file object may be a pipe, or is empty, or the'
                ' file object itself does not support seek/tell')
                LOG.error(msg)
                return None
            else:
                raise


LOG = Logger(log_dir='/var/log/restclient', logger='restclient',
             log_file_name='restclient.log', level=logging.DEBUG).getlog()


class RESTClient(object):

    def __init__(self, ip='127.0.0.1', port=8888,
                 ssl_enabled=False, verify=False,
                 token_path='/etc/zvmsdk/token.dat'):
        # SSL enable or not
        if ssl_enabled:
            self.base_url = "https://" + ip + ":" + str(port)
        else:
            self.base_url = "http://" + ip + ":" + str(port)
        # if value of verify is str, means its value is
        # the path of CA certificate
        if type(verify) == str:
            if not os.path.exists(verify):
                raise CACertNotFound('CA certificate file not found.')
        self.verify = verify
        self.token_path = token_path

    def _check_arguments(self, api_name, *args, **kwargs):
        # check api_name exist or not
        if api_name not in DATABASE.keys():
            msg = "API name %s not exist." % api_name
            raise APINameNotFound(msg)
        # check args count is valid
        count = DATABASE[api_name]['args_required']
        if len(args) < count:
            msg = "Missing some args,please check:%s." % args
            raise ArgsFormatError(msg)
        if len(args) > count:
            msg = "Too many args,please check:%s." % args
            raise ArgsFormatError(msg)

    def _get_admin_token(self, path):
        if os.path.exists(path):
            TOKEN_LOCK.acquire()
            try:
                with open(path, 'r') as fd:
                    token = fd.read().strip()
            except Exception:
                raise TokenFileOpenError('token file open failed.')
            finally:
                TOKEN_LOCK.release()
        else:
            raise TokenNotFound('token file not found.')
        return token

    def _get_token(self):
        _headers = {'Content-Type': 'application/json'}
        admin_token = self._get_admin_token(self.token_path)
        _headers['X-Admin-Token'] = admin_token

        url = self.base_url + '/token'
        method = 'POST'
        response = requests.request(method, url, headers=_headers,
                                    verify=self.verify)
        if response.status_code == 503:
            # service unavailable
            raise ServiceUnavailable(response)
        else:
            try:
                token = response.headers['X-Auth-Token']
            except KeyError:
                raise UnexpectedResponse(response)

        return token

    def _get_url_body_headers(self, api_name, *args, **kwargs):
        headers = {}
        headers['Content-Type'] = 'application/json'
        count_params_in_path = DATABASE[api_name]['params_path']
        func = DATABASE[api_name]['request']
        url, body = func(count_params_in_path, *args, **kwargs)

        # For image upload, the api is image_upload(image_name, source_url,
        # image_meta), valid keys for image_meta are os_version, md5sum,
        # also put the image size in request headers.
        if api_name in ['image_upload', 'image_download']:
            headers['Content-Type'] = 'application/octet-stream'

        if api_name == 'image-upload':
            additional_headers = args[count_params_in_path + 1]
            headers.update(additional_headers)

        if count_params_in_path > 0:
            url = url % tuple(args[0:count_params_in_path])

        full_url = '%s%s' % (self.base_url, url)
        return full_url, body, headers

    def _process_rest_response(self, response):
        content_type = response.headers.get('Content-Type')
        if content_type not in ['application/json',
                                'application/octet-stream']:
            LOG.error("Request returned failure status %s.",
                       response.status_code)

            # Currently, all the response content from zvmsdk wsgi are
            # 'application/json' or application/octet-stream type.
            # If it is not, the response may be sent by HTTP server due
            # to internal server error or time out,
            # it is an unexpected response to the rest client.
            # If new content-type is added to the response by sdkwsgi, the
            # parsing function here is also required to change.
            raise UnexpectedResponse(response)

        # Read body into string if it isn't obviously image data
        if content_type == 'application/octet-stream':
            # Do not read all response in memory when downloading an image.
            body_iter = self._close_after_stream(response, CHUNKSIZE)
        else:
            body_iter = None
#             # TODO check if response.text is same with response.content
#             content = response.text
#             if content_type and content_type.startswith('application/json'):
#                 # Let's use requests json method, it should take care of
#                 # response encoding
#                 body_iter = response.json()
#             else:
#                 body_iter = six.StringIO(content)
#                 try:
#                     body_iter = json.loads(''.join([c for c in body_iter]))
#                 except ValueError:
#                     body_iter = None

        return response, body_iter

    def api_request(self, url, method='GET', body=None, headers=None,
                    **kwargs):

        _headers = {}
        _headers.update(headers or {})
        if body is not None and not isinstance(body, six.string_types):
            try:
                body = json.dumps(body)
            except TypeError:
                # if data is a file-like object
                body = body
        _headers['X-Auth-Token'] = self._get_token()

        content_type = headers['Content-Type']
        kwargs['stream'] = content_type == 'application/octet-stream'

        # log what is send to server
        self.log_curl_request(method, url, headers, body, kwargs)

        response = requests.request(method, url, data=body,
                                    headers=_headers,
                                    verify=self.verify,
                                    **kwargs)
        return response

    def call(self, api_name, *args, **kwargs):
        try:
            # check validation of arguments
            self._check_arguments(api_name, *args, **kwargs)
            # get method by api_name
            method = DATABASE[api_name]['method']

            # get url,body with api_name and method
            url, body, headers = self._get_url_body_headers(api_name,
                                                        *args, **kwargs)
            response = self.api_request(url, method, body=body,
                                        headers=headers)

            # change response to SDK format
            resp, body_iter = self._process_rest_response(response)

            # return res_dict.get('output', None)
            if api_name == 'image_export':
                # resp is the response, body is the iterator
                # TODO check the status codes
                if resp.status_code == '204':
                    return None, resp

                checksum = resp.headers.get('content-md5', None)

                # Response header may contains content-md5, here it is the
                # whole image's checksum
                if checksum is not None:
                    body = self.integrity_iter(body_iter, checksum)
                # Call add
                if body is None:
                    msg = ('Image has no data.')
                    LOG.warning(msg)
                    # TODO throw exception, change the target
                target_file = '/tmp/target'
                self.save_image(body_iter, target_file)
                # TODO: return a dict to indicate the success.
            results = json.loads(resp.content)
        except TokenFileOpenError as err:
            errmsg = REST_REQUEST_ERROR[1][4] % {'error': err.msg}
            results = REST_REQUEST_ERROR[0]
            results.update({'rs': 4, 'errmsg': errmsg, 'output': ''})
        except TokenNotFound as err:
            errmsg = REST_REQUEST_ERROR[1][2] % {'error': err.msg}
            results = REST_REQUEST_ERROR[0]
            results.update({'rs': 2, 'errmsg': errmsg, 'output': ''})
        except UnexpectedResponse as err:
            errmsg = REST_REQUEST_ERROR[1][3] % ({
                'url': err.resp.url, 'status': err.resp.status_code,
                'reason': err.resp.reason, 'text': err.resp.text})
            results = REST_REQUEST_ERROR[0]
            results.update({'rs': 3, 'errmsg': errmsg, 'output': ''})
        except ServiceUnavailable as err:
            errmsg = SERVICE_UNAVAILABLE_ERROR[1][2] % {
                'reason': err.resp.reason, 'text': err.resp.text}
            results = SERVICE_UNAVAILABLE_ERROR[0]
            results.update({'rs': 2, 'errmsg': errmsg, 'output': ''})
        except Exception as err:
            errmsg = REST_REQUEST_ERROR[1][1] % {'error': six.text_type(err)}
            results = REST_REQUEST_ERROR[0]
            results.update({'rs': 1, 'errmsg': errmsg, 'output': ''})

        return results

    def log_curl_request(self, method, url, headers, data, kwargs):
        curl = ['curl -g -i -X %s' % method]

        headers = copy.deepcopy(headers)

        for (key, value) in headers.items():
            header = '-H \'%s: %s\'' % (key, value)
            curl.append(header)

        if data and isinstance(data, six.string_types):
            curl.append('-d \'%s\'' % data)

        curl.append(url)

        msg = ' '.join([item for item in curl])
        LOG.debug(msg)
        LOG.debug("The send request is: %s" % msg)

    def _close_after_stream(self, response, chunk_size):
        """Iterate over the content and ensure the response is closed after."""
        # Yield each chunk in the response body
        for chunk in response.iter_content(chunk_size=chunk_size):
            yield chunk
        # Once we're done streaming the body, ensure everything is closed.
        # This will return the connection to the HTTPConnectionPool in urllib3
        # and ideally reduce the number of HTTPConnectionPool full warnings.
        response.close()

    def integrity_iter(iter, checksum):
        """Check image data integrity.
        :param iter: iterator of image file
        :param checksum: the checksum of the image
        :raises: IOError
        """
        md5sum = hashlib.md5()
        for chunk in iter:
            yield chunk
            if isinstance(chunk, six.string_types):
                chunk = six.b(chunk)
            md5sum.update(chunk)
        md5sum = md5sum.hexdigest()
        if md5sum != checksum:
            raise IOError(errno.EPIPE,
                'Corrupt image download. Checksum was %s expected %s' %
                (md5sum, checksum))

    def save_image(self, data, path):
        """Save an image to the specified path.
        :param data: binary data of the image
        :param path: path to save the image to
        """
        with open(path, 'wb') as image:
            for chunk in data:
                image.write(chunk)
