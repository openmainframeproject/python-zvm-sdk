# Copyright 2017,2020 IBM Corp.
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


import os
import six
import shutil

from zvmsdk import config
from zvmsdk import dist
from zvmsdk import exception
from zvmsdk import log
from zvmsdk import smtclient
from zvmsdk import database
from zvmsdk import utils as zvmutils


_VMOPS = None
CONF = config.CONF
LOG = log.LOG


def get_vmops():
    global _VMOPS
    if _VMOPS is None:
        _VMOPS = VMOps()
    return _VMOPS


class VMOps(object):

    def __init__(self):
        self._smtclient = smtclient.get_smtclient()
        self._dist_manager = dist.LinuxDistManager()
        self._pathutils = zvmutils.PathUtils()
        self._namelist = zvmutils.get_namelist()
        self._GuestDbOperator = database.GuestDbOperator()
        self._ImageDbOperator = database.ImageDbOperator()

    def get_power_state(self, userid):
        """Get power status of a z/VM instance."""
        return self._smtclient.get_power_state(userid)

    def _get_cpu_num_from_user_dict(self, dict_info):
        cpu_num = 0
        for inf in dict_info:
            if 'CPU ' in inf:
                cpu_num += 1
        return cpu_num

    def _get_max_memory_from_user_dict(self, dict_info):
        with zvmutils.expect_invalid_resp_data():
            mem = dict_info[0].split(' ')[4]
            return zvmutils.convert_to_mb(mem) * 1024

    def get_info(self, userid):
        power_stat = self.get_power_state(userid)
        perf_info = self._smtclient.get_image_performance_info(userid)

        if perf_info:
            try:
                max_mem_kb = int(perf_info['max_memory'].split()[0])
                mem_kb = int(perf_info['used_memory'].split()[0])
                num_cpu = int(perf_info['guest_cpus'])
                cpu_time_us = int(perf_info['used_cpu_time'].split()[0])
            except (ValueError, TypeError, IndexError, AttributeError,
                    KeyError) as err:
                LOG.error('Parse performance_info encounter error: %s',
                          str(perf_info))
                raise exception.SDKInternalError(msg=str(err),
                                                    modID='guest')

            return {'power_state': power_stat,
                    'max_mem_kb': max_mem_kb,
                    'mem_kb': mem_kb,
                    'num_cpu': num_cpu,
                    'cpu_time_us': cpu_time_us}
        else:
            # virtual machine in shutdown state or not exists
            dict_info = self._smtclient.get_user_direct(userid)
            return {
                'power_state': power_stat,
                'max_mem_kb': self._get_max_memory_from_user_dict(dict_info),
                'mem_kb': 0,
                'num_cpu': self._get_cpu_num_from_user_dict(dict_info),
                'cpu_time_us': 0}

    def get_adapters_info(self, userid):
        adapters_info = self._smtclient.get_adapters_info(userid)
        if not adapters_info:
            msg = 'Get network information failed on: %s' % userid
            LOG.error(msg)
            raise exception.SDKInternalError(msg=msg, modID='guest')
        return {'adapters': adapters_info}

    def instance_metadata(self, instance, content, extra_md):
        pass

    def add_instance_metadata(self):
        pass

    def is_reachable(self, userid):
        """Reachable through IUCV communication channel."""
        return self._smtclient.get_guest_connection_status(userid)

    def guest_start(self, userid):
        """"Power on z/VM instance."""
        LOG.info("Begin to power on vm %s", userid)
        self._smtclient.guest_start(userid)
        LOG.info("Complete power on vm %s", userid)

    def guest_stop(self, userid, **kwargs):
        LOG.info("Begin to power off vm %s", userid)
        self._smtclient.guest_stop(userid, **kwargs)
        LOG.info("Complete power off vm %s", userid)

    def guest_softstop(self, userid, **kwargs):
        LOG.info("Begin to soft power off vm %s", userid)
        self._smtclient.guest_softstop(userid, **kwargs)
        LOG.info("Complete soft power off vm %s", userid)

    def guest_pause(self, userid):
        LOG.info("Begin to pause vm %s", userid)
        self._smtclient.guest_pause(userid)
        LOG.info("Complete pause vm %s", userid)

    def guest_unpause(self, userid):
        LOG.info("Begin to unpause vm %s", userid)
        self._smtclient.guest_unpause(userid)
        LOG.info("Complete unpause vm %s", userid)

    def guest_reboot(self, userid):
        """Reboot a guest vm."""
        LOG.info("Begin to reboot vm %s", userid)
        self._smtclient.guest_reboot(userid)
        LOG.info("Complete reboot vm %s", userid)

    def guest_reset(self, userid):
        """Reset z/VM instance."""
        LOG.info("Begin to reset vm %s", userid)
        self._smtclient.guest_reset(userid)
        LOG.info("Complete reset vm %s", userid)

    def live_migrate_vm(self, userid, destination, parms, action):
        """Move an eligible, running z/VM(R) virtual machine transparently
        from one z/VM system to another within an SSI cluster."""
        # Check guest state is 'on'
        state = self.get_power_state(userid)
        if state != 'on':
            LOG.error("Failed to live migrate guest %s, error: "
                    "guest is inactive, cann't perform live migrate." %
                    userid)
            raise exception.SDKConflictError(modID='guest', rs=1,
                                             userid=userid)
        # Do live migrate
        if action.lower() == 'move':
            LOG.info("Moving the specific vm %s", userid)
            self._smtclient.live_migrate_move(userid, destination, parms)
            LOG.info("Complete move vm %s", userid)

        if action.lower() == 'test':
            LOG.info("Testing the eligiblity of specific vm %s", userid)
            self._smtclient.live_migrate_test(userid, destination)

    def create_vm(self, userid, cpu, memory, disk_list,
                  user_profile, max_cpu, max_mem, ipl_from,
                  ipl_param, ipl_loadparam, dedicate_vdevs, loaddev):
        """Create z/VM userid into user directory for a z/VM instance."""
        LOG.info("Creating the user directory for vm %s", userid)

        info = self._smtclient.create_vm(userid, cpu, memory,
                                   disk_list, user_profile,
                                   max_cpu, max_mem, ipl_from,
                                   ipl_param, ipl_loadparam,
                                   dedicate_vdevs, loaddev)

        # add userid into smapi namelist
        self._smtclient.namelist_add(self._namelist, userid)
        return info

    def create_disks(self, userid, disk_list):
        LOG.info("Beging to create disks for vm: %(userid)s, list: %(list)s",
                 {'userid': userid, 'list': disk_list})
        user_direct = self._smtclient.get_user_direct(userid)

        exist_disks = []
        for ent in user_direct:
            if ent.strip().startswith('MDISK'):
                md_vdev = ent.split()[1].strip()
                exist_disks.append(md_vdev)

        if exist_disks:
            start_vdev = hex(int(max(exist_disks), 16) + 1)[2:].rjust(4, '0')
        else:
            start_vdev = None
        info = self._smtclient.add_mdisks(userid, disk_list, start_vdev)

        LOG.info("Complete create disks for vm: %s", userid)
        return info

    def delete_disks(self, userid, vdev_list):
        LOG.info("Begin to delete disk on vm: %(userid), vdev list: %(list)s",
                 {'userid': userid, 'list': vdev_list})

        # not support delete disks when guest is active
        if self._smtclient.get_power_state(userid) == 'on':
            func = 'delete disks when guest is active'
            raise exception.SDKFunctionNotImplementError(func)

        self._smtclient.remove_mdisks(userid, vdev_list)
        LOG.info("Complete delete disks for vm: %s", userid)

    def guest_config_minidisks(self, userid, disk_info):
        LOG.info("Begin to configure disks on vm: %(userid), info: %(info)s",
                 {'userid': userid, 'info': disk_info})
        if disk_info != []:
            self._smtclient.process_additional_minidisks(userid, disk_info)
            LOG.info("Complete configure disks for vm: %s", userid)
        else:
            LOG.info("No disk to handle on %s." % userid)

    def guest_grow_root_volume(self, userid, os_version):
        """ Punch the grow partition script to the target guest. """
        LOG.debug('Begin to punch grow partition commands to guest: %s',
                  userid)
        linuxdist = self._dist_manager.get_linux_dist(os_version)()
        # get configuration commands
        config_cmds = linuxdist.get_extend_partition_cmds()
        # Creating tmp file with these cmds
        temp_folder = self._pathutils.get_guest_temp_path(userid)
        file_path = os.path.join(temp_folder, 'gpartvol.sh')
        LOG.debug('Creating file %s to contain root partition extension '
                  'commands' % file_path)
        with open(file_path, "w") as f:
            f.write(config_cmds)
        try:
            self._smtclient.punch_file(userid, file_path, "X")
        finally:
            LOG.debug('Removing the folder %s ', temp_folder)
            shutil.rmtree(temp_folder)

    def is_powered_off(self, instance_name):
        """Return True if the instance is powered off."""
        return self._smtclient.get_power_state(instance_name) == 'off'

    def delete_vm(self, userid):
        """Delete z/VM userid for the instance."""
        LOG.info("Begin to delete vm %s", userid)
        self._smtclient.delete_vm(userid)

        # remove userid from smapi namelist
        self._smtclient.namelist_remove(self._namelist, userid)
        LOG.info("Complete delete vm %s", userid)

    def execute_cmd(self, userid, cmdStr):
        """Execute commands on the guest vm."""
        LOG.debug("executing cmd: %s", cmdStr)
        return self._smtclient.execute_cmd(userid, cmdStr)

    def set_hostname(self, userid, hostname, os_version):
        """Punch a script that used to set the hostname of the guest.

        :param str guest: the user id of the guest
        :param str hostname: the hostname of the guest
        :param str os_version: version of guest operation system
        """
        tmp_path = self._pathutils.get_guest_temp_path(userid)
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        tmp_file = tmp_path + '/hostname.sh'

        lnxdist = self._dist_manager.get_linux_dist(os_version)()
        lines = lnxdist.generate_set_hostname_script(hostname)
        with open(tmp_file, 'w') as f:
            f.writelines(lines)

        requestData = "ChangeVM " + userid + " punchfile " + \
                            tmp_file + " --class x"
        LOG.debug("Punch script to guest %s to set hostname" % userid)

        try:
            self._smtclient._request(requestData)
        except exception.SDKSMTRequestFailed as err:
            msg = ("Failed to punch set_hostname script to userid '%s'. SMT "
                   "error: %s" % (userid, err.format_message()))
            LOG.error(msg)
            raise exception.SDKSMTRequestFailed(err.results, msg)
        finally:
            self._pathutils.clean_temp_folder(tmp_path)

    def guest_deploy(self, userid, image_name, transportfiles=None,
                     remotehost=None, vdev=None, hostname=None,
                     skipdiskcopy=False):
        LOG.info("Begin to deploy image on vm %s", userid)
        if not skipdiskcopy:
            os_version = self._smtclient.image_get_os_distro(image_name)
        else:
            os_version = image_name
        if not self._smtclient.is_rhcos(os_version):
            self._smtclient.guest_deploy(userid, image_name, transportfiles,
                                         remotehost, vdev, skipdiskcopy)

            # punch scripts to set hostname
            if (transportfiles is None) and hostname:
                self.set_hostname(userid, hostname, os_version)
        else:
            self._smtclient.guest_deploy_rhcos(userid, image_name,
                            transportfiles, remotehost, vdev, hostname,
                            skipdiskcopy)

    def guest_capture(self, userid, image_name, capture_type='rootonly',
                      compress_level=6):
        LOG.info("Begin to capture vm %(userid), image name is %(name)s",
                 {'userid': userid, 'name': image_name})
        self._smtclient.guest_capture(userid, image_name,
                                       capture_type=capture_type,
                                       compress_level=compress_level)
        LOG.info("Complete capture image on vm %s", userid)

    def guest_list(self):
        return self._smtclient.get_vm_list()

    def guest_list_hypervisor(self):
        return self._smtclient.get_all_user_direct()

    def get_definition_info(self, userid, **kwargs):
        check_command = ["nic_coupled"]
        direct_info = self._smtclient.get_user_direct(userid)
        info = {}
        info['user_direct'] = direct_info

        for k, v in kwargs.items():
            if k in check_command:
                if (k == 'nic_coupled'):
                    info['nic_coupled'] = False
                    nstr = "NICDEF %s TYPE QDIO LAN SYSTEM" % v
                    for inf in direct_info:
                        if nstr in inf:
                            info['nic_coupled'] = True
                            break
            else:
                raise exception.SDKInvalidInputFormat(
                    msg=("invalid check option for user direct: %s") % k)

        return info

    def get_console_output(self, userid):
        def append_to_log(log_data, log_path):
            LOG.debug('log_data: %(log_data)r, log_path: %(log_path)r',
                         {'log_data': log_data, 'log_path': log_path})
            with open(log_path, 'a+') as fp:
                fp.write(log_data)

            return log_path

        LOG.info("Begin to capture console log on vm %s", userid)
        log_size = CONF.guest.console_log_size * 1024
        console_log = self._smtclient.get_user_console_output(userid)

        log_path = self._pathutils.get_console_log_path(userid)
        # TODO: need consider shrink log file size
        append_to_log(console_log, log_path)

        log_fp = open(log_path, 'rb')
        try:
            log_data, remaining = zvmutils.last_bytes(log_fp, log_size)
        except Exception as err:
            msg = ("Failed to truncate console log, error: %s" %
                   six.text_type(err))
            LOG.error(msg)
            raise exception.SDKInternalError(msg)

        if remaining > 0:
            LOG.info('Truncated console log returned, %d bytes ignored' %
                     remaining)

        LOG.info("Complete get console output on vm %s", userid)
        return log_data

    def check_guests_exist_in_db(self, userids, raise_exc=True):
        if not isinstance(userids, list):
            # convert userid string to list
            userids = [userids]

        all_userids = self.guest_list()

        userids_not_in_db = list(set(userids) - set(all_userids))
        if userids_not_in_db:
            if raise_exc:
                # log and raise exception
                userids_not_in_db = ' '.join(userids_not_in_db)
                LOG.error("Guest '%s' does not exist in guests database" %
                          userids_not_in_db)
                raise exception.SDKObjectNotExistError(
                    obj_desc=("Guest '%s'" % userids_not_in_db), modID='guest')
            else:
                return False
        else:
            userids_migrated = self._GuestDbOperator.get_migrated_guest_list()
            userids_in_migrated = list(set(userids) & set(userids_migrated))

            # case1 userid has been migrated.
            if userids_in_migrated:
                if raise_exc:
                    migrated_userids = ' '.join(userids_in_migrated)
                    LOG.error("Guest(s) '%s' has been migrated." %
                              migrated_userids)
                    raise exception.SDKObjectNotExistError(
                                obj_desc=("Guest(s) '%s'" % migrated_userids),
                                modID='guest')
                else:
                    return False

            flag = True
            for uid in userids:
                # case2 userid has been shudown and started on other host.
                if zvmutils.check_userid_on_others(uid):
                    flag = False
                    comment = self._GuestDbOperator.get_comments_by_userid(uid)
                    comment['migrated'] = 1
                    action = "update guest '%s' in database" % uid
                    with zvmutils.log_and_reraise_sdkbase_error(action):
                        self._GuestDbOperator.update_guest_by_userid(
                                        uid, comments=comment)
            return flag

    def live_resize_cpus(self, userid, count):
        # Check power state is 'on'
        state = self.get_power_state(userid)
        if state != 'on':
            LOG.error("Failed to live resize cpus of guest %s, error: "
                      "guest is inactive, cann't perform live resize." %
                      userid)
            raise exception.SDKConflictError(modID='guest', rs=1,
                                             userid=userid)
        # Do live resize
        self._smtclient.live_resize_cpus(userid, count)

        LOG.info("Complete live resize cpu on vm %s", userid)

    def resize_cpus(self, userid, count):
        LOG.info("Begin to resize cpu on vm %s", userid)
        # Do resize
        self._smtclient.resize_cpus(userid, count)
        LOG.info("Complete resize cpu on vm %s", userid)

    def live_resize_memory(self, userid, memory):
        # Check power state is 'on'
        state = self.get_power_state(userid)
        if state != 'on':
            LOG.error("Failed to live resize memory of guest %s, error: "
                      "guest is inactive, cann't perform live resize." %
                      userid)
            raise exception.SDKConflictError(modID='guest', rs=1,
                                             userid=userid)
        # Do live resize
        self._smtclient.live_resize_memory(userid, memory)

        LOG.info("Complete live resize memory on vm %s", userid)

    def resize_memory(self, userid, memory):
        LOG.info("Begin to resize memory on vm %s", userid)
        # Do resize
        self._smtclient.resize_memory(userid, memory)
        LOG.info("Complete resize memory on vm %s", userid)
