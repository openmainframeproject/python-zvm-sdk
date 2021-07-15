# Copyright 2017,2021 IBM Corp.
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


import time
from zvmsdk import config
from zvmsdk import constants as const
from zvmsdk import exception
from zvmsdk import log
from zvmsdk import smtclient
from zvmsdk import utils as zvmutils


_HOSTOPS = None
CONF = config.CONF
LOG = log.LOG


def get_hostops():
    global _HOSTOPS
    if _HOSTOPS is None:
        _HOSTOPS = HOSTOps()
    return _HOSTOPS


class HOSTOps(object):
    def __init__(self):
        self._smtclient = smtclient.get_smtclient()
        self._volume_infos = {}
        self._volumes = None
        self.cache_expiration = time.time()

    def get_info(self):
        inv_info = self._smtclient.get_host_info()
        host_info = {}

        with zvmutils.expect_invalid_resp_data(inv_info):
            host_info['zcc_userid'] = inv_info['zcc_userid']
            host_info['zvm_host'] = inv_info['zvm_host']
            host_info['vcpus'] = int(inv_info['lpar_cpu_total'])
            host_info['vcpus_used'] = int(inv_info['lpar_cpu_used'])
            host_info['cpu_info'] = {}
            host_info['cpu_info'] = {'architecture': const.ARCHITECTURE,
                                     'cec_model': inv_info['cec_model'], }
            mem_mb = zvmutils.convert_to_mb(inv_info['lpar_memory_total'])
            host_info['memory_mb'] = mem_mb
            mem_mb_used = zvmutils.convert_to_mb(inv_info['lpar_memory_used'])
            host_info['memory_mb_used'] = mem_mb_used
            host_info['hypervisor_type'] = const.HYPERVISOR_TYPE
            verl = inv_info['hypervisor_os'].split()[1].split('.')
            version = int(''.join(verl))
            host_info['hypervisor_version'] = version
            host_info['hypervisor_hostname'] = inv_info['hypervisor_name']
            host_info['ipl_time'] = inv_info['ipl_time']
        disk_pool = CONF.zvm.disk_pool
        if disk_pool is None:
            dp_info = {'disk_total': 0, 'disk_used': 0, 'disk_available': 0}
        else:
            diskpool_name = disk_pool.split(':')[1]
            dp_info = self.diskpool_get_info(diskpool_name)
        host_info.update(dp_info)

        return host_info

    def guest_list(self):
        guest_list = self._smtclient.get_all_user_direct()
        with zvmutils.expect_invalid_resp_data(guest_list):
            return guest_list

    def _cache_enabled(self):
        return CONF.monitor.cache_interval > 0

    def diskpool_get_volumes(self, pool_name):
        if self._cache_enabled():
            if (time.time() > self.cache_expiration):
                self._volumes = None
            if self._volumes:
                return self._volumes
            else:
                self._volumes = self._smtclient.get_diskpool_volumes(pool_name)
                self.cache_expiration = time.time() + \
                    float(CONF.monitor.cache_interval)
                with zvmutils.expect_invalid_resp_data(self._volumes):
                    return self._volumes
        else:
            self._volumes = self._smtclient. \
                get_diskpool_volumes(pool_name)
            with zvmutils.expect_invalid_resp_data(self._volumes):
                return self._volumes

    def get_volume_info(self, volume_name):
        update_needed = False
        with zvmutils.expect_invalid_resp_data():
            if self._volume_infos is not None:
                volume_info = self._volume_infos.get(volume_name)
                if not volume_info:
                    update_needed = True
                else:
                    return volume_info
            else:
                update_needed = True
            if update_needed:
                # results of get_volume_info() is the format like:
                # {'IAS100': { 'volume_type': '3390-54',
                # 'volume_size': '60102'},
                # 'IAS101': { 'volume_type': '3390-09',
                # 'volume_size': '60102'}}
                self._volume_infos = self._smtclient.get_volume_info()
                volume_info = self._volume_infos.get(volume_name)
                if not volume_info:
                    msg = ("Not found the volume info for the"
                           " volume %(volume)s: make sure the volume"
                           " is in the disk_pool configured for sdkserver.") \
                          % {'volume': volume_name}
                    raise exception.ZVMNotFound(msg=msg)
                else:
                    return volume_info

    def diskpool_get_info(self, pool):
        dp_info = self._smtclient.get_diskpool_info(pool)
        with zvmutils.expect_invalid_resp_data(dp_info):
            for k in list(dp_info.keys()):
                s = dp_info[k].strip().upper()
                if s.endswith('G'):
                    sl = s[:-1].split('.')
                    n1, n2 = int(sl[0]), int(sl[1])
                    if n2 >= 5:
                        n1 += 1
                    dp_info[k] = n1
                elif s.endswith('M'):
                    n_mb = int(s[:-3])
                    n_gb, n_ad = n_mb // 1024, n_mb % 1024
                    if n_ad >= 512:
                        n_gb += 1
                    dp_info[k] = n_gb
                else:
                    exp = "ending with a 'G' or 'M'"
                    errmsg = ("Invalid diskpool size format: %(invalid)s; "
                        "Expected: %(exp)s") % {'invalid': s, 'exp': exp}
                    LOG.error(errmsg)
                    raise exception.SDKInternalError(msg=errmsg)

        return dp_info
