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

import mock
import six

from zvmsdk import config
from zvmsdk import hostops
from zvmsdk import exception
from zvmsdk.tests.unit import base

CONF = config.CONF


class SDKHostOpsTestCase(base.SDKTestCase):
    def setUp(self):
        self._hostops = hostops.get_hostops()

    @mock.patch("zvmsdk.smtclient.SMTClient.get_all_user_direct")
    def test_guest_list(self, get_all_user_direct):
        self._hostops.guest_list()
        get_all_user_direct.assert_called_once_with()

    @mock.patch("zvmsdk.hostops.HOSTOps.diskpool_get_info")
    @mock.patch("zvmsdk.smtclient.SMTClient.get_host_info")
    def test_get_host_info(self, get_host_info, diskpool_get_info):
        get_host_info.return_value = {
            "zcc_userid": "FAKEUSER",
            "zvm_host": "FAKENODE",
            "zhcp": "fakehcp.fake.com",
            "cec_vendor": "FAKE",
            "cec_model": "2097",
            "hypervisor_os": "z/VM 6.1.0",
            "hypervisor_name": "fakenode",
            "architecture": "s390x",
            "lpar_cpu_total": "10",
            "lpar_cpu_used": "10",
            "lpar_memory_total": "16G",
            "lpar_memory_used": "16.0G",
            "lpar_memory_offline": "0",
            "ipl_time": "IPL at 03/13/14 21:43:12 EDT",
            }
        diskpool_get_info.return_value = {
            "disk_total": 406105,
            "disk_used": 367263,
            "disk_available": 38843,
            }
        host_info = self._hostops.get_info()
        get_host_info.assert_called_once_with()
        base.set_conf('zvm', 'disk_pool', 'ECKD:TESTPOOL')
        diskpool = CONF.zvm.disk_pool.split(':')[1]
        diskpool_get_info.assert_called_once_with(diskpool)
        self.assertEqual(host_info['vcpus'], 10)
        self.assertEqual(host_info['hypervisor_version'], 610)
        self.assertEqual(host_info['disk_total'], 406105)

        # Test disk_pool is None
        base.set_conf('zvm', 'disk_pool', None)
        host_info = self._hostops.get_info()
        self.assertEqual(host_info['disk_total'], 0)
        self.assertEqual(host_info['disk_used'], 0)
        self.assertEqual(host_info['disk_available'], 0)

    @mock.patch("zvmsdk.smtclient.SMTClient.get_diskpool_info")
    def test_get_diskpool_info(self, get_diskpool_info):
        get_diskpool_info.return_value = {
            "disk_total": "406105.3G",
            "disk_used": "367262.6G",
            "disk_available": "38842.7M",
            }
        dp_info = self._hostops.diskpool_get_info("fakepool")
        get_diskpool_info.assert_called_once_with("fakepool")
        self.assertEqual(dp_info['disk_total'], 406105)
        self.assertEqual(dp_info['disk_used'], 367263)
        self.assertEqual(dp_info['disk_available'], 38)

    @mock.patch("time.time")
    @mock.patch("zvmsdk.hostops.HOSTOps._cache_enabled")
    @mock.patch("zvmsdk.smtclient.SMTClient.get_diskpool_volumes")
    def test_diskpool_get_volumes(self, get_diskpool_vols,
            cache_enable, mock_time):
        self._hostops._volumes = {}
        volumes = {'diskpool_volumes': 'IAS100 IAS101'}
        get_diskpool_vols.return_value = volumes
        cache_enable.return_value = True
        mock_time.return_value = 1
        diskpool_vols = self._hostops.diskpool_get_volumes("fakepool")
        get_diskpool_vols.assert_called_once_with("fakepool")
        self.assertEqual(diskpool_vols['diskpool_volumes'], 'IAS100 IAS101')
        # Test has cache data
        volumes = {'diskpool_volumes': 'IAS400 IAS501'}
        base.set_conf('monitor', 'cache_interval', '60')
        self._hostops._volumes = volumes
        diskpool_vols = self._hostops.diskpool_get_volumes("fakepool2")
        self.assertEqual(1, get_diskpool_vols.call_count)
        self.assertEqual(diskpool_vols['diskpool_volumes'], 'IAS400 IAS501')

    @mock.patch("zvmsdk.smtclient.SMTClient.get_volume_info")
    def test_get_volume_info(self, get_vol_infos):
        self._hostops._volume_infos = None
        get_vol_infos.return_value = {'IASFBA': {'volume_type': '9336-ET',
            'volume_size': '564718'},
            'IAS1CM': {'volume_type': '3390-09',
            'volume_size': '60102'}}
        volume_info = self._hostops.get_volume_info('IAS1CM')
        get_vol_infos.assert_called_once_with()
        self.assertEqual(volume_info['volume_type'], '3390-09')
        self.assertEqual(volume_info['volume_size'], '60102')
        # Test cache is not None
        self._hostops._volume_infos = get_vol_infos.return_value
        volume_info = self._hostops.get_volume_info('IASFBA')
        self.assertEqual(volume_info['volume_type'], '9336-ET')
        self.assertEqual(volume_info['volume_size'], '564718')
        # Test cache not None, but volume not in the disk_pool
        try:
            volume_info = self._hostops.get_volume_info('IASFBB')
        except exception.ZVMNotFound as exc:
            exc = six.text_type(exc)
            if "Not found the volume info in " in exc:
                pass
        self.assertEqual(2, get_vol_infos.call_count)
