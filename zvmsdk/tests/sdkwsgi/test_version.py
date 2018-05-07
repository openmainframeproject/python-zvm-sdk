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


from zvmsdk.tests.sdkwsgi import api_sample
from zvmsdk.tests.sdkwsgi import base
from zvmsdk.tests.sdkwsgi import test_utils


class VersionTestCase(base.ZVMConnectorBaseTestCase):
    def __init__(self, methodName='runTest'):
        super(VersionTestCase, self).__init__(methodName)
        self.apibase = api_sample.APITestBase()

    def setUp(self):
        super(VersionTestCase, self).setUp()
        self.client = test_utils.TestzCCClient()
        self.record_logfile_position()

    def test_version(self):
        resp = self.client.api_request(url='/')
        self.assertEqual(200, resp.status_code)
        self.apibase.verify_result('test_version', resp.content)

    def test_not_found(self):
        resp = self.client.api_request(url='/notfound')
        self.assertEqual(404, resp.status_code)
