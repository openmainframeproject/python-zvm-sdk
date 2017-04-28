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


from zvmsdk import vmops
from zvmsdk import hostops
from zvmsdk import config
from zvmsdk import networkops


CONF = config.CONF


class SDKAPI(object):
    """Compute action interfaces."""

    def __init__(self):
        self._vmops = vmops.get_vmops()
        self._hostops = hostops.get_hostops()
        self._networkops = networkops.get_networkops()

    def power_on(self, vm_id):
        """Power on a virtual machine."""
        self._vmops.power_on(vm_id)

    def get_power_state(self, vm_id):
        """Returns power state."""
        return self._vmops.get_power_state(vm_id)

    def get_vm_info(self, vm_id):
        """Returns a dict containing:
        :param power_state: the running state, one of on | off
        :param max_mem_kb: (int) the maximum memory in KBytes allowed
        :param mem_kb: (int) the memory in KBytes used by the instance
        :param num_cpu: (int) the number of virtual CPUs for the instance
        :param cpu_time_ns: (int) the CPU time used in nanoseconds
        """
        return self._vmops.get_info(vm_id)

    def get_host_info(self):
        """ Retrieve host information including host, memory, disk etc.
        :returns: Dictionary describing resources
        """
        host = CONF.zvm.host
        return self._hostops.get_host_info(host)

    def get_diskpool_info(self):
        """ Retrieve diskpool information.
        :returns: Dictionary describing diskpool usage info
        """
        host = CONF.zvm.host
        pool = CONF.zvm.diskpool
        return self._hostops.get_diskpool_info(host, pool)

    def list_vms(self):
        """Return the names of all the VMs known to the virtualization
        layer, as a list.
        """
        return self._hostops.get_vm_list()
