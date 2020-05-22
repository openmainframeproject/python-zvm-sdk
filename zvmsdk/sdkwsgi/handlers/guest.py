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

"""Handler for the root of the sdk API."""

import json
import six
import threading
import webob.exc

from zvmconnector import connector
from zvmsdk import config
from zvmsdk import log
from zvmsdk import returncode
from zvmsdk.sdkwsgi.handlers import tokens
from zvmsdk.sdkwsgi.schemas import guest
from zvmsdk.sdkwsgi import util
from zvmsdk.sdkwsgi import validation
from zvmsdk import utils


_VMACTION = None
_VMHANDLER = None
CONF = config.CONF
LOG = log.LOG
CONF = config.CONF


class VMHandler(object):
    def __init__(self):
        self.client = connector.ZVMConnector(connection_type='socket',
                                             ip_addr=CONF.sdkserver.bind_addr,
                                             port=CONF.sdkserver.bind_port)

    @validation.schema(guest.create)
    def create(self, body):
        guest = body['guest']

        userid = guest['userid']
        vcpus = guest['vcpus']
        memory = guest['memory']

        kwargs_list = {}
        guest_keys = guest.keys()
        if 'disk_list' in guest_keys:
            kwargs_list['disk_list'] = guest['disk_list']
        if 'user_profile' in guest_keys:
            kwargs_list['user_profile'] = guest['user_profile']
        if 'max_cpu' in guest_keys:
            kwargs_list['max_cpu'] = guest['max_cpu']
        if 'max_mem' in guest_keys:
            kwargs_list['max_mem'] = guest['max_mem']
        if 'ipl_from' in guest_keys:
            kwargs_list['ipl_from'] = guest['ipl_from']
        if 'ipl_param' in guest_keys:
            kwargs_list['ipl_param'] = guest['ipl_param']
        if 'ipl_loadparam' in guest_keys:
            kwargs_list['ipl_loadparam'] = guest['ipl_loadparam']
        if 'dedicate_vdevs' in guest_keys:
            kwargs_list['dedicate_vdevs'] = guest['dedicate_vdevs']
        if 'loaddev' in guest_keys:
            kwargs_list['loaddev'] = guest['loaddev']

        info = self.client.send_request('guest_create', userid, vcpus,
                                        memory, **kwargs_list)

        return info

    def list(self):
        # list all guest on the given host
        info = self.client.send_request('guest_list')
        return info

    def list_hypervisor(self):
        # list all guest on the given hypervisor
        info = self.client.send_request('guest_list_hypervisor')
        return info

    @validation.query_schema(guest.userid_list_query)
    def get_power_state_real(self, req, userid):
        info = self.client.send_request('guest_get_power_state_real', userid)
        return info

    @validation.query_schema(guest.userid_list_query)
    def get_info(self, req, userid):
        info = self.client.send_request('guest_get_info', userid)
        return info

    @validation.query_schema(guest.userid_list_query)
    def get_user_direct(self, req, userid):
        info = self.client.send_request('guest_get_user_direct', userid)
        return info

    @validation.query_schema(guest.userid_list_query)
    def get_adapters(self, req, userid):
        info = self.client.send_request('guest_get_adapters_info', userid)
        return info

    @validation.query_schema(guest.userid_list_query)
    def get_definition_info(self, req, userid):
        info = self.client.send_request('guest_get_definition_info', userid)
        return info

    @validation.query_schema(guest.userid_list_query)
    def get_power_state(self, req, userid):
        info = self.client.send_request('guest_get_power_state', userid)
        return info

    def delete(self, userid):
        info = self.client.send_request('guest_delete', userid)
        return info

    def delete_nic(self, userid, vdev, body):
        active = body.get('active', False)
        active = util.bool_from_string(active, strict=True)

        info = self.client.send_request('guest_delete_nic', userid, vdev,
                                        active=active)
        return info

    @validation.query_schema(guest.userid_list_array_query)
    def inspect_stats(self, req, userid_list):
        info = self.client.send_request('guest_inspect_stats',
                                        userid_list)
        return info

    @validation.query_schema(guest.userid_list_array_query)
    def inspect_vnics(self, req, userid_list):
        info = self.client.send_request('guest_inspect_vnics',
                                        userid_list)
        return info

    # @validation.query_schema(guest.nic_DB_info)
    # FIXME: the above validation will fail with "'dict' object has no
    # attribute 'dict_of_lists'"
    def get_nic_DB_info(self, req, userid=None, nic_id=None, vswitch=None):
        info = self.client.send_request('guests_get_nic_info', userid=userid,
                                        nic_id=nic_id, vswitch=vswitch)
        return info

    @validation.schema(guest.create_nic)
    def create_nic(self, userid, body=None):
        nic = body['nic']

        vdev = nic.get('vdev', None)
        nic_id = nic.get('nic_id', None)
        mac_addr = nic.get('mac_addr', None)
        active = nic.get('active', False)
        active = util.bool_from_string(active, strict=True)

        info = self.client.send_request('guest_create_nic', userid,
                                        vdev=vdev, nic_id=nic_id,
                                        mac_addr=mac_addr,
                                        active=active)
        return info

    @validation.schema(guest.create_network_interface)
    def create_network_interface(self, userid, body=None):
        interface = body['interface']
        version = interface['os_version']
        networks = interface.get('guest_networks', None)
        active = interface.get('active', False)
        active = util.bool_from_string(active, strict=True)
        info = self.client.send_request('guest_create_network_interface',
                                        userid, os_version=version,
                                        guest_networks=networks,
                                        active=active)
        return info

    @validation.schema(guest.delete_network_interface)
    def delete_network_interface(self, userid, body=None):
        interface = body['interface']
        version = interface['os_version']
        vdev = interface['vdev']
        active = interface.get('active', False)
        active = util.bool_from_string(active, strict=True)
        info = self.client.send_request('guest_delete_network_interface',
                                        userid, version, vdev,
                                        active=active)
        return info

    @validation.schema(guest.create_disks)
    def create_disks(self, userid, body=None):
        disk_info = body['disk_info']
        disk_list = disk_info.get('disk_list', None)
        info = self.client.send_request('guest_create_disks', userid,
                                        disk_list)
        return info

    @validation.schema(guest.config_minidisks)
    def config_minidisks(self, userid, body=None):
        disk_info = body['disk_info']
        disk_list = disk_info.get('disk_list', None)
        info = self.client.send_request('guest_config_minidisks', userid,
                                        disk_list)
        return info

    @validation.schema(guest.delete_disks)
    def delete_disks(self, userid, body=None):
        vdev_info = body['vdev_info']
        vdev_list = vdev_info.get('vdev_list', None)

        info = self.client.send_request('guest_delete_disks', userid,
                                        vdev_list)

        return info

    @validation.schema(guest.nic_couple_uncouple)
    def nic_couple_uncouple(self, userid, vdev, body):
        info = body['info']

        active = info.get('active', False)
        active = util.bool_from_string(active, strict=True)

        couple = util.bool_from_string(info['couple'], strict=True)

        if couple:
            info = self.client.send_request('guest_nic_couple_to_vswitch',
                                            userid, vdev, info['vswitch'],
                                            active=active)
        else:
            info = self.client.send_request('guest_nic_uncouple_from_vswitch',
                                            userid, vdev,
                                            active=active)
        return info


class VMAction(object):

    def __init__(self):
        self.client = connector.ZVMConnector(connection_type='socket',
                                             ip_addr=CONF.sdkserver.bind_addr,
                                             port=CONF.sdkserver.bind_port)
        self.dd_semaphore = threading.BoundedSemaphore(
            value=CONF.wsgi.max_concurrent_deploy_capture)

    def start(self, userid, body):
        info = self.client.send_request('guest_start', userid)

        return info

    @validation.schema(guest.stop)
    def stop(self, userid, body):
        timeout = body.get('timeout', None)
        poll_interval = body.get('poll_interval', None)

        info = self.client.send_request('guest_stop', userid,
                                        timeout=timeout,
                                        poll_interval=poll_interval)

        return info

    @validation.schema(guest.softstop)
    def softstop(self, userid, body):
        timeout = body.get('timeout', None)
        poll_interval = body.get('poll_interval', None)

        info = self.client.send_request('guest_softstop', userid,
                                        timeout=timeout,
                                        poll_interval=poll_interval)

        return info

    def pause(self, userid, body):
        info = self.client.send_request('guest_pause', userid)

        return info

    def unpause(self, userid, body):
        info = self.client.send_request('guest_unpause', userid)

        return info

    def reboot(self, userid, body):
        info = self.client.send_request('guest_reboot', userid)

        return info

    def reset(self, userid, body):
        info = self.client.send_request('guest_reset', userid)

        return info

    def get_console_output(self, userid, body):
        info = self.client.send_request('guest_get_console_output',
                                        userid)

        return info

    @validation.schema(guest.register_vm)
    def register_vm(self, userid, body):
        meta = body['meta']
        net_set = body['net_set']
        port_macs = None
        if 'port_macs' in body.keys():
            port_macs = body['port_macs']
        info = self.client.send_request('guest_register',
                                userid, meta, net_set, port_macs)
        return info

    @validation.schema(guest.deregister_vm)
    def deregister_vm(self, userid, body):
        info = self.client.send_request('guest_deregister', userid)
        return info

    @validation.schema(guest.live_migrate_vm)
    def live_migrate_vm(self, userid, body):
        # dest_zcc_userid default as ''
        dest_zcc_userid = body.get('dest_zcc_userid', '')
        destination = body['destination']
        operation = body.get('operation', {})
        parms = body['parms']

        info = self.client.send_request('guest_live_migrate',
                                userid, dest_zcc_userid, destination,
                                parms, operation)
        return info

    @validation.schema(guest.resize_cpus)
    def resize_cpus(self, userid, body):
        cpu_cnt = body['cpu_cnt']
        info = self.client.send_request('guest_resize_cpus',
                                        userid, cpu_cnt)

        return info

    @validation.schema(guest.resize_cpus)
    def live_resize_cpus(self, userid, body):
        cpu_cnt = body['cpu_cnt']
        info = self.client.send_request('guest_live_resize_cpus',
                                        userid, cpu_cnt)

        return info

    @validation.schema(guest.resize_mem)
    def resize_mem(self, userid, body):
        size = body['size']
        info = self.client.send_request('guest_resize_mem',
                                        userid, size)

        return info

    @validation.schema(guest.resize_mem)
    def live_resize_mem(self, userid, body):
        size = body['size']
        info = self.client.send_request('guest_live_resize_mem',
                                        userid, size)

        return info

    @validation.schema(guest.grow_root_volume)
    def grow_root_volume(self, userid, body=None):
        info = self.client.send_request('guest_grow_root_volume', userid,
                                        body['os_version'])
        return info

    @validation.schema(guest.deploy)
    def deploy(self, userid, body):
        image_name = body['image']

        transportfiles = body.get('transportfiles', None)
        remotehost = body.get('remotehost', None)
        vdev = body.get('vdev', None)
        hostname = body.get('hostname', None)
        skipdiskcopy = body.get('skipdiskcopy', False)

        request_info = ("action: 'deploy', userid: %(userid)s,"
                        "transportfiles: %(trans)s, remotehost: %(remote)s,"
                        "vdev: %(vdev)s, skipdiskcopy: %(skipdiskcopy)s" %
                        {'userid': userid, 'trans': transportfiles,
                         'remote': remotehost, 'vdev': vdev,
                         'skipdiskcopy': skipdiskcopy,
                         })

        info = None
        dd_allowed = self.dd_semaphore.acquire(blocking=False)
        if not dd_allowed:
            error_def = returncode.errors['serviceUnavail']
            info = error_def[0]
            err_msg = error_def[1][1] % {'req': request_info}
            info.update({'rs': 1,
                         'errmsg': err_msg,
                         'output': ''})
            LOG.error(err_msg)
            return info

        try:
            LOG.debug("WSGI sending deploy requests. %s" % request_info)
            info = self.client.send_request('guest_deploy', userid,
                                            image_name,
                                            transportfiles=transportfiles,
                                            remotehost=remotehost,
                                            vdev=vdev, hostname=hostname,
                                            skipdiskcopy=skipdiskcopy)
        finally:
            try:
                self.dd_semaphore.release()
                LOG.debug("WSGI deploy request finished, %s."
                          "Resource released." % request_info)
            except Exception as err:
                err_msg = ("Failed to release deploy resource in WSGI."
                           "Error: %s, request info: %s" %
                           (six.text_type(err), request_info))
                LOG.error(err_msg)

        return info

    @validation.schema(guest.capture)
    def capture(self, userid, body):
        image_name = body['image']

        capture_type = body.get('capture_type', 'rootonly')
        compress_level = body.get('compress_level', 6)

        request_info = ("action: 'capture', userid: %(userid)s,"
                        "image name: %(image)s, capture type: %(cap)s,"
                        "compress level: %(level)s" %
                        {'userid': userid, 'image': image_name,
                         'cap': capture_type, 'level': compress_level
                         })
        info = None
        capture_allowed = self.dd_semaphore.acquire(blocking=False)
        if not capture_allowed:
            error_def = returncode.errors['serviceUnavail']
            info = error_def[0]
            err_msg = error_def[1][1] % {'req': request_info}
            info.update({'rs': 1,
                         'errmsg': err_msg,
                         'output': ''})
            LOG.error(err_msg)
            return info

        try:
            LOG.debug("WSGI sending capture requests. %s" % request_info)
            info = self.client.send_request('guest_capture', userid,
                                            image_name,
                                            capture_type=capture_type,
                                            compress_level=compress_level)
        finally:
            try:
                self.dd_semaphore.release()
                LOG.debug("WSGI capture request finished, %s."
                          "Resource released." % request_info)
            except Exception as err:
                err_msg = ("Failed to release capture resource in WSGI."
                           "Error: %s, request info: %s" %
                           (six.text_type(err), request_info))
                LOG.error(err_msg)

        return info


def get_action():
    global _VMACTION
    if _VMACTION is None:
        _VMACTION = VMAction()
    return _VMACTION


def get_handler():
    global _VMHANDLER
    if _VMHANDLER is None:
        _VMHANDLER = VMHandler()
    return _VMHANDLER


@util.SdkWsgify
@tokens.validate
def guest_get_power_state_real(req):

    def _guest_get_power_state_real(req, userid):
        action = get_handler()
        return action.get_power_state_real(req, userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_get_power_state_real(req, userid)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_get_info(req):

    def _guest_get_info(req, userid):
        action = get_handler()
        return action.get_info(req, userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_get_info(req, userid)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_get_user_direct(req):

    def _guest_get_user_direct(req, userid):
        action = get_handler()

        return action.get_user_direct(req, userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_get_user_direct(req, userid)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_get_adapters_info(req):

    def _guest_get_adapters_info(req, userid):
        action = get_handler()
        return action.get_adapters(req, userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_get_adapters_info(req, userid)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_get(req):

    def _guest_get(req, userid):
        action = get_handler()
        return action.get_definition_info(req, userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_get(req, userid)

    # info we got looks like:
    # {'user_direct': [u'USER RESTT305 PASSW0RD 1024m 1024m G',
    #                  u'INCLUDE OSDFLT']}
    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_get_power_state(req):

    def _guest_get_power_state(req, userid):
        action = get_handler()
        return action.get_power_state(req, userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_get_power_state(req, userid)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_create(req):

    def _guest_create(req):
        action = get_handler()
        body = util.extract_json(req.body)

        return action.create(body=body)

    info = _guest_create(req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_already_exists)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_list(req):
    def _guest_list():
        action = get_handler()
        return action.list()

    info = _guest_list()
    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    req.response.status = 200
    return req.response

@util.SdkWsgify
@tokens.validate
def guest_list_hypervisor(req):
    def _guest_list_hypervisor():
        action = get_handler()
        return action.list_hypervisor()

    info = _guest_list_hypervisor()
    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    req.response.status = 200
    return req.response

@util.SdkWsgify
@tokens.validate
def guest_action(req):

    def _guest_action(userid, req):
        action = get_action()
        body = util.extract_json(req.body)
        if len(body) == 0 or 'action' not in body:
            msg = 'action not exist or is empty'
            LOG.info(msg)
            raise webob.exc.HTTPBadRequest(explanation=msg)

        method = body['action']
        func = getattr(action, method, None)
        if func:
            body.pop('action')
            return func(userid, body=body)
        else:
            msg = 'action %s is invalid' % method
            raise webob.exc.HTTPBadRequest(msg)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_action(userid, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found_and_conflict)
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_delete(req):

    def _guest_delete(userid):
        action = get_handler()
        return action.delete(userid)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_delete(userid)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info, default=200)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_delete_nic(req):
    def _guest_delete_nic(userid, vdev, req):
        action = get_handler()
        body = util.extract_json(req.body)

        return action.delete_nic(userid, vdev, body)

    userid = util.wsgi_path_item(req.environ, 'userid')
    vdev = util.wsgi_path_item(req.environ, 'vdev')

    info = _guest_delete_nic(userid, vdev, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info, default=200)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_create_nic(req):

    def _guest_create_nic(userid, req):
        action = get_handler()
        body = util.extract_json(req.body)

        return action.create_nic(userid, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_create_nic(userid, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_couple_uncouple_nic(req):

    def _guest_couple_uncouple_nic(userid, vdev, req):
        action = get_handler()
        body = util.extract_json(req.body)

        return action.nic_couple_uncouple(userid, vdev, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')
    vdev = util.wsgi_path_item(req.environ, 'vdev')

    info = _guest_couple_uncouple_nic(userid, vdev, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_create_network_interface(req):

    def _guest_create_network_interface(userid, req):
        action = get_handler()
        body = util.extract_json(req.body)

        return action.create_network_interface(userid, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_create_network_interface(userid, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_delete_network_interface(req):

    def _guest_delete_network_interface(userid, req):
        action = get_handler()
        body = util.extract_json(req.body)

        return action.delete_network_interface(userid, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')
    info = _guest_delete_network_interface(userid, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info)
    req.response.content_type = 'application/json'
    return req.response


def _get_userid_list(req):
    userids = []
    if 'userid' in req.GET.keys():
        userid = req.GET.get('userid')
        userid = userid.strip(' ,')
        userid = userid.replace(' ', '')
        userids.extend(userid.split(','))

    return userids


@util.SdkWsgify
@tokens.validate
def guest_get_stats(req):

    userid_list = _get_userid_list(req)

    def _guest_get_stats(req, userid_list):
        action = get_handler()
        return action.inspect_stats(req, userid_list)

    info = _guest_get_stats(req, userid_list)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_get_interface_stats(req):

    userid_list = _get_userid_list(req)

    def _guest_get_interface_stats(req, userid_list):
        action = get_handler()
        return action.inspect_vnics(req, userid_list)

    info = _guest_get_interface_stats(req, userid_list)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guests_get_nic_info(req):

    def _guests_get_nic_DB_info(req, userid=None, nic_id=None, vswitch=None):
        action = get_handler()
        return action.get_nic_DB_info(req, userid=userid, nic_id=nic_id,
                                      vswitch=vswitch)
    userid = req.GET.get('userid', None)
    nic_id = req.GET.get('nic_id', None)
    vswitch = req.GET.get('vswitch', None)

    info = _guests_get_nic_DB_info(req, userid=userid, nic_id=nic_id,
                                   vswitch=vswitch)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_config_disks(req):

    def _guest_config_minidisks(userid, req):
        action = get_handler()
        body = util.extract_json(req.body)
        return action.config_minidisks(userid, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')

    info = _guest_config_minidisks(userid, req)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_create_disks(req):

    def _guest_create_disks(userid, req):
        action = get_handler()
        body = util.extract_json(req.body)
        return action.create_disks(userid, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')

    info = _guest_create_disks(userid, req)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def guest_delete_disks(req):

    def _guest_delete_disks(userid, req):
        action = get_handler()
        body = util.extract_json(req.body)
        return action.delete_disks(userid, body=body)

    userid = util.wsgi_path_item(req.environ, 'userid')

    info = _guest_delete_disks(userid, req)

    info_json = json.dumps(info)
    req.response.status = util.get_http_code_from_sdk_return(info, default=200)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    return req.response
