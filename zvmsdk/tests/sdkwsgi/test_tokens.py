#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import unittest

from zvmsdk.tests.sdkwsgi import api_sample
from zvmsdk.tests.sdkwsgi import test_sdkwsgi


class TokenTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(TokenTestCase, self).__init__(methodName)
        self.apibase = api_sample.APITestBase()

    def setUp(self):
        self.client = test_sdkwsgi.TestSDKClient()

    def test_tokens_validation(self):
        resp = self.client.api_request(url='/token')
        self.assertEqual(200, resp.status_code)

        self.assertEqual(200, resp.headers['X-Auth-Token'])
