# Virtual Machine Utilities for Systems Management Ultra Thin Layer
#
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

import re
import subprocess
from subprocess import CalledProcessError
import time

from smtLayer import msgs

modId = 'VMU'
version = '1.0.0'         # Version of this script


def disableEnableDisk(rh, userid, vaddr, option):
    """
    Disable or enable a disk.

    Input:
       Request Handle:
          owning userid
          virtual address
          option ('-e': enable, '-d': disable)

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - rc from the chccwdev command or IUCV transmission.
          rs        - rs from the chccwdev command or IUCV transmission.
          results   - possible error message from the IUCV transmission.
    """

    rh.printSysLog("Enter vmUtils.disableEnableDisk, userid: " + userid +
        " addr: " + vaddr + " option: " + option)

    results = {
              'overallRC': 0,
              'rc': 0,
              'rs': 0,
              'response': ''
             }

    """
    Can't guarantee the success of online/offline disk, need to wait
    Until it's done because we may detach the disk after -d option
    or use the disk after the -e option
    """
    for secs in [0.1, 0.4, 1, 1.5, 3, 7, 15, 32, 30, 30,
                60, 60, 60, 60, 60]:
        strCmd = "sudo /sbin/chccwdev " + option + " " + vaddr + " 2>&1"
        results = execCmdThruIUCV(rh, userid, strCmd)
        if results['overallRC'] == 0:
            break
        elif (results['overallRC'] == 2 and results['rc'] == 8 and
            results['rs'] == 1 and option == '-d'):
            # Linux does not know about the disk being disabled.
            # Ok, nothing to do.  Treat this as a success.
            results = {'overallRC': 0, 'rc': 0, 'rs': 0, 'response': ''}
            break
        time.sleep(secs)

    rh.printSysLog("Exit vmUtils.disableEnableDisk, rc: " +
        str(results['overallRC']))
    return results


def execCmdThruIUCV(rh, userid, strCmd, hideInLog=[]):
    """
    Send a command to a virtual machine using IUCV.

    Input:
       Request Handle
       Userid of the target virtual machine
       Command string to send
       (Optional) List of strCmd words (by index) to hide in
          sysLog by replacing the word with "<hidden>".

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, 2: failure
          rc        - RC returned from iucvclnt if overallRC != 0.
          rs        - RS returned from iucvclnt if overallRC != 0.
          errno     - Errno returned from iucvclnt if overallRC != 0.
          response  - Output of the iucvclnt command or this routine.

    Notes:
       1) This routine does not use the Request Handle printLn function.
          This is because an error might be expected and we might desire
          to suppress it.  Instead, any error messages are put in the
          response dictionary element that is returned.
    """
    if len(hideInLog) == 0:
        rh.printSysLog("Enter vmUtils.execCmdThruIUCV, userid: " +
                       userid + " cmd: " + strCmd)
    else:
        logCmd = strCmd.split(' ')
        for i in hideInLog:
            logCmd[i] = '<hidden>'
        rh.printSysLog("Enter vmUtils.execCmdThruIUCV, userid: " +
                       userid + " cmd: " + ' '.join(logCmd))

    iucvpath = '/opt/zthin/bin/IUCV/'
    results = {
              'overallRC': 0,
              'rc': 0,
              'rs': 0,
              'errno': 0,
              'response': [],
             }

    cmd = ['sudo',
           iucvpath + "iucvclnt",
           userid,
           strCmd]
    try:
        results['response'] = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                close_fds=True)
        if isinstance(results['response'], bytes):
            results['response'] = bytes.decode(results['response'])
    except CalledProcessError as e:
        msg = []
        results['overallRC'] = 2
        results['rc'] = e.returncode
        output = bytes.decode(e.output)

        match = re.search('Return code (.+?),', output)
        if match:
            try:
                results['rc'] = int(match.group(1))
            except ValueError:
                # Return code in response from IUCVCLNT is not an int.
                msg = msgs.msg['0311'][1] % (modId, userid, strCmd,
                    results['rc'], match.group(1), output)

        if not msg:
            # We got the rc. Now, get the rs.
            match = re.search('Reason code (.+?)\.', output)
            if match:
                try:
                    results['rs'] = int(match.group(1))
                except ValueError:
                    # Reason code in response from IUCVCLNT is not an int.
                    msg = msgs.msg['0312'][1] % (modId, userid, strCmd,
                        results['rc'], match.group(1), output)

        if msg:
            # Already produced an error message.
            pass
        elif results['rc'] == 1:
            # Command was not authorized or a generic Linux error.
            msg = msgs.msg['0313'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        elif results['rc'] == 2:
            # IUCV client parameter error.
            msg = msgs.msg['0314'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        elif results['rc'] == 4:
            # IUCV socket error
            msg = msgs.msg['0315'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        elif results['rc'] == 8:
            # Executed command failed
            msg = msgs.msg['0316'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        elif results['rc'] == 16:
            # File Transport failed
            msg = msgs.msg['0317'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        elif results['rc'] == 32:
            # IUCV server file was not found on this system.
            msg += msgs.msg['0318'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        else:
            # Unrecognized IUCV client error
            msg = msgs.msg['0319'][1] % (modId, userid, strCmd,
                results['rc'], results['rs'], output)
        results['response'] = msg

    except Exception as e:
        # Other exceptions from this system (i.e. not the managed system).
        results = msgs.msg['0421'][0]
        msg = msgs.msg['0421'][1] % (modId, strCmd,
            type(e).__name__, str(e))
        results['response'] = msg

    rh.printSysLog("Exit vmUtils.execCmdThruIUCV, rc: " +
                   str(results['rc']))
    return results


def getPerfInfo(rh, useridlist):
    """
    Get the performance information for a userid

    Input:
       Request Handle
       Userid to query <- may change this to a list later.

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - RC returned from SMCLI if overallRC = 0.
          rs        - RS returned from SMCLI if overallRC = 0.
          errno     - Errno returned from SMCLI if overallRC = 0.
          response  - Stripped and reformatted output of the SMCLI command.
    """
    rh.printSysLog("Enter vmUtils.getPerfInfo, userid: " + useridlist)
    parms = ["-T", rh.userid,
             "-c", "1"]
    results = invokeSMCLI(rh, "Image_Performance_Query", parms)
    if results['overallRC'] != 0:
        # SMCLI failed.
        rh.printLn("ES", results['response'])
        rh.printSysLog("Exit vmUtils.getPerfInfo, rc: " +
                       str(results['overallRC']))
        return results

    lines = results['response'].split("\n")
    usedTime = 0
    totalCpu = 0
    totalMem = 0
    usedMem = 0
    try:
        for line in lines:
            if "Used CPU time:" in line:
                usedTime = line.split()[3].strip('"')
                # Value is in us, need make it seconds
                usedTime = int(usedTime) / 1000000
            if "Guest CPUs:" in line:
                totalCpu = line.split()[2].strip('"')
            if "Max memory:" in line:
                totalMem = line.split()[2].strip('"')
                # Value is in Kb, need to make it Mb
                totalMem = int(totalMem) / 1024
            if "Used memory:" in line:
                usedMem = line.split()[2].strip('"')
                usedMem = int(usedMem) / 1024
    except Exception as e:
        msg = msgs.msg['0412'][1] % (modId, type(e).__name__,
            str(e), results['response'])
        rh.printLn("ES", msg)
        results['overallRC'] = 4
        results['rc'] = 4
        results['rs'] = 412

    if results['overallRC'] == 0:
        memstr = "Total Memory: %iM\n" % totalMem
        usedmemstr = "Used Memory: %iM\n" % usedMem
        procstr = "Processors: %s\n" % totalCpu
        timestr = "CPU Used Time: %i sec\n" % usedTime
        results['response'] = memstr + usedmemstr + procstr + timestr
    rh.printSysLog("Exit vmUtils.getPerfInfo, rc: " +
                   str(results['rc']))
    return results


def installFS(rh, vaddr, mode, fileSystem, diskType):
    """
    Install a filesystem on a virtual machine's dasd.

    Input:
       Request Handle:
          userid - Userid that owns the disk
       Virtual address as known to the owning system.
       Access mode to use to get the disk.
       Disk Type - 3390 or 9336

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - RC returned from SMCLI if overallRC = 0.
          rs        - RS returned from SMCLI if overallRC = 0.
          errno     - Errno returned from SMCLI if overallRC = 0.
          response  - Output of the SMCLI command.
    """

    rh.printSysLog("Enter vmUtils.installFS, userid: " + rh.userid +
        ", vaddr: " + str(vaddr) + ", mode: " + mode + ", file system: " +
        fileSystem + ", disk type: " + diskType)

    results = {
              'overallRC': 0,
              'rc': 0,
              'rs': 0,
              'errno': 0,
             }

    out = ''
    diskAccessed = False

    # Get access to the disk.
    cmd = ["sudo",
           "/opt/zthin/bin/linkdiskandbringonline",
           rh.userid,
           vaddr,
           mode]
    strCmd = ' '.join(cmd)
    rh.printSysLog("Invoking: " + strCmd)
    try:
        # Sometimes the disk is not ready: sleep and retry
        try_num = 0
        for sleep_secs in [0.2, 0.4, 0.8, 1.6, 2, 2, -1]:
            try_num += 1
            try:
                out = subprocess.check_output(cmd, close_fds=True)
                rh.printSysLog("Run `%s` successfully." % strCmd)
                diskAccessed = True
                break
            except Exception as e:
                if sleep_secs > 0:
                    rh.printSysLogForDebug("Num %d try `%s` failed ("
                                           "retry after %s seconds): "
                                           "exception=%s msg=%s" % (
                                           try_num, strCmd, sleep_secs,
                                           type(e).__name__, str(e)))
                    time.sleep(sleep_secs)
                else:
                    res = invokeSMCLI(rh, "Image_Query_DM", ['-T', rh.userid])
                    user_direct = res['response']
                    rh.printSysLogForDebug("Failed to link %s, its user directory "
                                           "is:%s." % (rh.userid, user_direct))
                    raise
        if isinstance(out, bytes):
            out = bytes.decode(out)
    except CalledProcessError as e:
        rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
            e.returncode, e.output))
        results = msgs.msg['0415'][0]
        results['rs'] = e.returncode
        rh.updateResults(results)
    except Exception as e:
        # All other exceptions.
        results = msgs.msg['0421'][0]
        rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
            type(e).__name__, str(e)))

    if results['overallRC'] == 0:
        """
        sample output:
        linkdiskandbringonline maint start time: 2017-03-03-16:20:48.011
        Success: Userid maint vdev 193 linked at ad35 device name dasdh
        linkdiskandbringonline exit time: 2017-03-03-16:20:52.150
        """
        match = re.search('Success:(.+?)\n', out)
        if match:
            parts = match.group(1).split()
            if len(parts) > 9:
                device = "/dev/" + parts[9]
            else:
                strCmd = ' '.join(cmd)
                rh.printLn("ES", msgs.msg['0416'][1] % (modId,
                    'Success:', 10, strCmd, out))
                results = msgs.msg['0416'][0]
                rh.updateResults(results)
        else:
            strCmd = ' '.join(cmd)
            rh.printLn("ES", msgs.msg['0417'][1] % (modId,
                'Success:', strCmd, out))
            results = msgs.msg['0417'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0 and diskType == "3390":
        # dasdfmt the disk
        cmd = ["sudo",
            "/sbin/dasdfmt",
            "-y",
            "-b", "4096",
            "-d", "cdl",
            "-v", device]
        strCmd = ' '.join(cmd)
        rh.printSysLog("Invoking: " + strCmd)
        try:
            out = subprocess.check_output(cmd, close_fds=True)
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            strCmd = " ".join(cmd)
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0 and diskType == "3390":
        # Settle the devices so we can do the partition.
        strCmd = ("which udevadm &> /dev/null && " +
            "udevadm settle || udevsettle")
        rh.printSysLog("Invoking: " + strCmd)
        try:
            subprocess.check_output(
                strCmd,
                stderr=subprocess.STDOUT,
                close_fds=True,
                shell=True)
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            strCmd = " ".join(cmd)
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0 and diskType == "3390":
        # Prepare the partition with fdasd
        cmd = ["sudo", "/sbin/fdasd", "-a", device]
        strCmd = ' '.join(cmd)
        rh.printSysLog("Invoking: " + strCmd)
        try:
            out = subprocess.check_output(cmd,
                stderr=subprocess.STDOUT, close_fds=True)
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0 and diskType == "9336":
        # Delete the existing partition in case the disk already
        # has a partition in it.
        cmd = "sudo /sbin/fdisk " + device + " << EOF\ng\nw\nEOF"
        rh.printSysLog("Invoking: sudo /sbin/fdisk " + device +
            " << EOF\\nd\\nw\\nEOF ")
        try:
            out = subprocess.check_output(cmd,
                stderr=subprocess.STDOUT,
                close_fds=True,
                shell=True)
            rh.printSysLog("Run `%s` success with output: %s"
                           % (cmd, out))
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, cmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, cmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0 and diskType == "9336":
        # Prepare the partition with fdisk
        cmd = "sudo /sbin/fdisk " + device + " << EOF\nn\np\n1\n\n\nw\nEOF"
        rh.printSysLog("Invoking: sudo /sbin/fdisk " + device +
            " << EOF\\nn\\np\\n1\\n\\n\\nw\\nEOF")
        try:
            # Sometimes the table is not ready: sleep and retry
            try_num = 0
            for sleep_secs in [0.1, 0.2, 0.3, 0.5, 1, 2, -1]:
                try_num += 1
                try:
                    out = subprocess.check_output(cmd,
                        stderr=subprocess.STDOUT,
                        close_fds=True,
                        shell=True)
                    rh.printSysLog("Run `%s` success with output: %s"
                                   % (cmd, out))
                    break
                except CalledProcessError as e:
                    if sleep_secs > 0:
                        rh.printSysLog("Num %d try `%s` failed ("
                                       "retry after %s seconds): "
                                       "rc=%d msg=%s" % (
                                        try_num, cmd, sleep_secs,
                                        e.returncode, e.output))
                        time.sleep(sleep_secs)
                    else:
                        raise
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, cmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, cmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0:
        # Settle the devices so we can do the partition.
        strCmd = ("which udevadm &> /dev/null && " +
            "udevadm settle || udevsettle")
        rh.printSysLog("Invoking: " + strCmd)
        try:
            subprocess.check_output(
                strCmd,
                stderr=subprocess.STDOUT,
                close_fds=True,
                shell=True)
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            strCmd = " ".join(cmd)
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['overallRC'] == 0:
        # Install the file system into the disk.
        device = device + "1"       # Point to first partition
        if fileSystem == 'swap':
            cmd = ["sudo", "mkswap", device]
        elif fileSystem == 'xfs':
            cmd = ["sudo", "mkfs.xfs", "-f", device]
        else:
            cmd = ["sudo", "mkfs", "-F", "-t", fileSystem, device]
        strCmd = ' '.join(cmd)
        rh.printSysLog("Invoking: " + strCmd)
        try:
            # Sometimes the device is not ready: sleep and retry
            try_num = 0
            for sleep_secs in [0.1, 0.2, 0.3, 0.5, 1, 2, -1]:
                try_num += 1
                try:
                    out = subprocess.check_output(cmd,
                                                  stderr=subprocess.STDOUT,
                                                  close_fds=True)
                    rh.printSysLog("Run `%s` successfully." % strCmd)
                    break
                except CalledProcessError as e:
                    if sleep_secs > 0:
                        rh.printSysLog("Num %d try `%s` failed ("
                                       "retry after %s seconds): "
                                       "rc=%d msg=%s" % (
                                           try_num, strCmd, sleep_secs,
                                           e.returncode, e.output))
                        time.sleep(sleep_secs)
                    else:
                        raise

            if isinstance(out, bytes):
                out = bytes.decode(out)
            rh.printLn("N", "File system: " + fileSystem +
                       " is installed.")
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                                                    e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                                                    type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)
    # TODO: diskAccessed hard code to True, because if linkdiskandbringonline
    # failed, can not set diskAccessed. will leave DASD undetached.
    # So always try to disconnect the disk. If this fixed in the future, need
    # remove this.
    diskAccessed = True
    if diskAccessed:
        # Give up the disk.
        cmd = ["sudo", "/opt/zthin/bin/offlinediskanddetach",
               rh.userid,
               vaddr]
        strCmd = ' '.join(cmd)
        rh.printSysLog("Invoking: " + strCmd)
        try:
            out = subprocess.check_output(cmd, close_fds=True)
            if isinstance(out, bytes):
                out = bytes.decode(out)
        except CalledProcessError as e:
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
            rh.updateResults(results)
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    rh.printSysLog("Exit vmUtils.installFS, rc: " + str(results['rc']))
    return results


def invokeSMCLI(rh, api, parms, hideInLog=[]):
    """
    Invoke SMCLI and parse the results.

    Input:
       Request Handle
       API name,
       SMCLI parms as an array
       (Optional) List of parms (by index) to hide in
          sysLog by replacing the parm with "<hidden>".

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - RC returned from SMCLI if overallRC = 0.
          rs        - RS returned from SMCLI if overallRC = 0.
          errno     - Errno returned from SMCLI if overallRC = 0.
          response  - String output of the SMCLI command.

    Note:
       - If the first three words of the header returned from smcli
         do not do not contain words that represent valid integer
         values or contain too few words then one or more error
         messages are generated. THIS SHOULD NEVER OCCUR !!!!
    """
    if len(hideInLog) == 0:
        rh.printSysLog("Enter vmUtils.invokeSMCLI, userid: " +
                       rh.userid + ", function: " + api +
                       ", parms: " + str(parms))
    else:
        logParms = parms
        for i in hideInLog:
            logParms[i] = '<hidden>'
        rh.printSysLog("Enter vmUtils.invokeSMCLI, userid: " +
               rh.userid + ", function: " + api +
               ", parms: " + str(logParms))
    goodHeader = False

    results = {
              'overallRC': 0,
              'rc': 0,
              'rs': 0,
              'errno': 0,
              'response': [],
              'strError': '',
             }

    cmd = []
    cmd.append('sudo')
    cmd.append('/opt/zthin/bin/smcli')
    cmd.append(api)
    cmd.append('--addRCheader')

    try:
        smcliResp = subprocess.check_output(cmd + parms,
            close_fds=True)
        if isinstance(smcliResp, bytes):
            smcliResp = bytes.decode(smcliResp, errors='replace')

        smcliResp = smcliResp.split('\n', 1)
        results['response'] = smcliResp[1]
        results['overallRC'] = 0
        results['rc'] = 0

    except CalledProcessError as e:
        strCmd = " ".join(cmd + parms)

        # Break up the RC header into its component parts.
        if e.output == '':
            smcliResp = ['']
        else:
            smcliResp = bytes.decode(e.output).split('\n', 1)

        # Split the header into its component pieces.
        rcHeader = smcliResp[0].split('(details)', 1)
        if len(rcHeader) == 0:
            rcHeader = ['', '']
        elif len(rcHeader) == 1:
            # No data after the details tag.  Add empty [1] value.
            rcHeader.append('')
        codes = rcHeader[0].split(' ')

        # Validate the rc, rs, and errno.
        if len(codes) < 3:
            # Unexpected number of codes.  Need at least 3.
            results = msgs.msg['0301'][0]
            results['response'] = msgs.msg['0301'][1] % (modId, api,
                strCmd, rcHeader[0], rcHeader[1])
        else:
            goodHeader = True
            # Convert the first word (overall rc from SMAPI) to an int
            # and set the SMT overall rc based on this value.
            orcError = False
            try:
                results['overallRC'] = int(codes[0])
                if results['overallRC'] not in [8, 24, 25]:
                    orcError = True
            except ValueError:
                goodHeader = False
                orcError = True
            if orcError:
                results['overallRC'] = 25    # SMCLI Internal Error
                results = msgs.msg['0302'][0]
                results['response'] = msgs.msg['0302'][1] % (modId,
                    api, codes[0], strCmd, rcHeader[0], rcHeader[1])

            # Convert the second word to an int and save as rc.
            try:
                results['rc'] = int(codes[1])
            except ValueError:
                goodHeader = False
                results = msgs.msg['0303'][0]
                results['response'] = msgs.msg['0303'][1] % (modId,
                    api, codes[1], strCmd, rcHeader[0], rcHeader[1])

            # Convert the second word to an int and save it as either
            # the rs or errno.
            try:
                word3 = int(codes[2])
                if results['overallRC'] == 8:
                    results['rs'] = word3    # Must be an rs
                elif results['overallRC'] == 25:
                    results['errno'] = word3    # Must be the errno
                # We ignore word 3 for everyone else and default to 0.
            except ValueError:
                goodHeader = False
                results = msgs.msg['0304'][0]
                results['response'] = msgs.msg['0304'][1] % (modId,
                    api, codes[1], strCmd, rcHeader[0], rcHeader[1])

        results['strError'] = rcHeader[1].lstrip()

        if goodHeader:
            # Produce a message that provides the error info.
            results['response'] = msgs.msg['0300'][1] % (modId,
                    api, results['overallRC'], results['rc'],
                    results['rs'], results['errno'],
                    strCmd, smcliResp[1])

    except Exception as e:
        # All other exceptions.
        strCmd = " ".join(cmd + parms)
        results = msgs.msg['0305'][0]
        results['response'] = msgs.msg['0305'][1] % (modId, strCmd,
            type(e).__name__, str(e))

    rh.printSysLog("Exit vmUtils.invokeSMCLI, rc: " +
        str(results['overallRC']))
    return results


def isLoggedOn(rh, userid):
    """
    Determine whether a virtual machine is logged on.

    Input:
       Request Handle:
          userid being queried

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - 0: if we got status.  Otherwise, it is the
                        error return code from the commands issued.
          rs        - Based on rc value.  For rc==0, rs is:
                      0: if we determined it is logged on.
                      1: if we determined it is logged off.
    """

    rh.printSysLog("Enter vmUtils.isLoggedOn, userid: " + userid)

    results = {
              'overallRC': 0,
              'rc': 0,
              'rs': 0,
             }

    cmd = ["sudo", "/sbin/vmcp", "query", "user", userid]
    strCmd = ' '.join(cmd)
    rh.printSysLog("Invoking: " + strCmd)
    try:
        subprocess.check_output(
            cmd,
            close_fds=True,
            stderr=subprocess.STDOUT)
    except CalledProcessError as e:
        search_pattern = '(^HCP\w\w\w045E|^HCP\w\w\w361E)'.encode()
        match = re.search(search_pattern, e.output)
        if match:
            # Not logged on
            results['rs'] = 1
        else:
            # Abnormal failure
            rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                e.returncode, e.output))
            results = msgs.msg['0415'][0]
            results['rs'] = e.returncode
    except Exception as e:
        # All other exceptions.
        results = msgs.msg['0421'][0]
        rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
            type(e).__name__, str(e)))

    rh.printSysLog("Exit vmUtils.isLoggedOn, overallRC: " +
        str(results['overallRC']) + " rc: " + str(results['rc']) +
        " rs: " + str(results['rs']))
    return results


def punch2reader(rh, userid, fileLoc, spoolClass):
    """
    Punch a file to a virtual reader of the specified virtual machine.

    Input:
       Request Handle - for general use and to hold the results
       userid         - userid of the virtual machine
       fileLoc        - File to send
       spoolClass     - Spool class

    Output:
       Request Handle updated with the results.
       Return code - 0: ok, non-zero: error
    """

    rh.printSysLog("Enter punch2reader.punchFile")
    results = {}

    # Setting rc to time out rc code as default and its changed during runtime
    results['rc'] = 9

    # Punch to the current user intially and then change the spool class.
    cmd = ["sudo", "/usr/sbin/vmur", "punch", "-r", fileLoc]
    strCmd = ' '.join(cmd)
    for secs in [1, 2, 3, 5, 10]:
        rh.printSysLog("Invoking: " + strCmd)
        try:
            results['response'] = subprocess.check_output(cmd,
                                        close_fds=True,
                                        stderr=subprocess.STDOUT)
            if isinstance(results['response'], bytes):
                results['response'] = bytes.decode(results['response'])
            results['rc'] = 0
            rh.updateResults(results)
            break
        except CalledProcessError as e:
            results['response'] = e.output
            # Check if we have concurrent instance of vmur active
            to_find = "A concurrent instance of vmur is already active"
            to_find = to_find.encode()
            if results['response'].find(to_find) == -1:
                # Failure in VMUR punch update the rc
                results['rc'] = 7
                break
            else:
                # if concurrent vmur is active try after sometime
                rh.printSysLog("Punch in use. Retrying after " +
                               str(secs) + " seconds")
                time.sleep(secs)
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]
            rh.updateResults(results)

    if results['rc'] == 7:
        # Failure while issuing vmur command (For eg: invalid file given)
        msg = msgs.msg['0401'][1] % (modId, fileLoc, userid,
                                     results['response'])
        rh.printLn("ES", msg)
        rh.updateResults(msgs.msg['0401'][0])

    elif results['rc'] == 9:
        # Failure due to vmur timeout
        msg = msgs.msg['0406'][1] % (modId, fileLoc)
        rh.printLn("ES", msg)
        rh.updateResults(msgs.msg['0406'][0])

    if rh.results['overallRC'] == 0:
        # On VMUR success change the class of the spool file
        spoolId = re.findall(r'\d+', str(results['response']))
        cmd = ["sudo", "vmcp", "change", "rdr", str(spoolId[0]), "class",
               spoolClass]
        strCmd = " ".join(cmd)
        rh.printSysLog("Invoking: " + strCmd)
        try:
            results['response'] = subprocess.check_output(cmd,
                                        close_fds=True,
                                        stderr=subprocess.STDOUT)
            if isinstance(results['response'], bytes):
                results['response'] = bytes.decode(results['response'])
            rh.updateResults(results)
        except CalledProcessError as e:
            msg = msgs.msg['0404'][1] % (modId,
                                         spoolClass,
                                         e.output)
            rh.printLn("ES", msg)
            rh.updateResults(msgs.msg['0404'][0])
            # Class change failed
            # Delete the punched file from current userid
            cmd = ["sudo", "vmcp", "purge", "rdr", spoolId[0]]
            strCmd = " ".join(cmd)
            rh.printSysLog("Invoking: " + strCmd)
            try:
                results['response'] = subprocess.check_output(cmd,
                                            close_fds=True,
                                            stderr=subprocess.STDOUT)
                if isinstance(results['response'], bytes):
                    results['response'] = bytes.decode(results['response'])
            # We only need to issue the printLn.
            # Don't need to change return/reason code values
            except CalledProcessError as e:
                msg = msgs.msg['0403'][1] % (modId,
                                             spoolId[0],
                                             e.output)
                rh.printLn("ES", msg)
            except Exception as e:
                # All other exceptions related to purge.
                # We only need to issue the printLn.
                # Don't need to change return/reason code values
                rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                    type(e).__name__, str(e)))
        except Exception as e:
            # All other exceptions related to change rdr.
            results = msgs.msg['0421'][0]
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            rh.updateResults(msgs.msg['0421'][0])

    if rh.results['overallRC'] == 0:
        # Transfer the file from current user to specified user
        cmd = ["sudo", "vmcp", "transfer", "*", "rdr", str(spoolId[0]), "to",
                userid, "rdr"]
        strCmd = " ".join(cmd)
        rh.printSysLog("Invoking: " + strCmd)
        try:
            results['response'] = subprocess.check_output(cmd,
                                        close_fds=True,
                                        stderr=subprocess.STDOUT)
            if isinstance(results['response'], bytes):
                results['response'] = bytes.decode(results['response'])
            rh.updateResults(results)
        except CalledProcessError as e:
            msg = msgs.msg['0424'][1] % (modId,
                                         fileLoc,
                                         userid, e.output)
            rh.printLn("ES", msg)
            rh.updateResults(msgs.msg['0424'][0])

            # Transfer failed so delete the punched file from current userid
            cmd = ["sudo", "vmcp", "purge", "rdr", spoolId[0]]
            strCmd = " ".join(cmd)
            rh.printSysLog("Invoking: " + strCmd)
            try:
                results['response'] = subprocess.check_output(cmd,
                                            close_fds=True,
                                            stderr=subprocess.STDOUT)
                if isinstance(results['response'], bytes):
                    results['response'] = bytes.decode(results['response'])
                # We only need to issue the printLn.
                # Don't need to change return/reason code values
            except CalledProcessError as e:
                msg = msgs.msg['0403'][1] % (modId,
                                             spoolId[0],
                                             e.output)
                rh.printLn("ES", msg)
            except Exception as e:
                # All other exceptions related to purge.
                rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                    type(e).__name__, str(e)))
        except Exception as e:
            # All other exceptions related to transfer.
            results = msgs.msg['0421'][0]
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            rh.updateResults(msgs.msg['0421'][0])

    rh.printSysLog("Exit vmUtils.punch2reader, rc: " +
        str(rh.results['overallRC']))
    return rh.results['overallRC']


def waitForOSState(rh, userid, desiredState, maxQueries=90, sleepSecs=5):
    """
    Wait for the virtual OS to go into the indicated state.

    Input:
       Request Handle
       userid whose state is to be monitored
       Desired state, 'up' or 'down', case sensitive
       Maximum attempts to wait for desired state before giving up
       Sleep duration between waits

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - RC returned from execCmdThruIUCV if overallRC = 0.
          rs        - RS returned from execCmdThruIUCV if overallRC = 0.
          errno     - Errno returned from execCmdThruIUCV if overallRC = 0.
          response  - Updated with an error message if wait times out.

    Note:

    """

    rh.printSysLog("Enter vmUtils.waitForOSState, userid: " + userid +
                           " state: " + desiredState +
                           " maxWait: " + str(maxQueries) +
                           " sleepSecs: " + str(sleepSecs))

    results = {}

    strCmd = "echo 'ping'"
    stateFnd = False

    for i in range(1, maxQueries + 1):
        results = execCmdThruIUCV(rh, rh.userid, strCmd)
        if results['overallRC'] == 0:
            if desiredState == 'up':
                stateFnd = True
                break
        else:
            if desiredState == 'down':
                stateFnd = True
                break

        if i < maxQueries:
            time.sleep(sleepSecs)

    if stateFnd is True:
        results = {
                'overallRC': 0,
                'rc': 0,
                'rs': 0,
            }
    else:
        maxWait = maxQueries * sleepSecs
        rh.printLn("ES", msgs.msg['0413'][1] % (modId, userid,
            desiredState, maxWait))
        results = msgs.msg['0413'][0]

    rh.printSysLog("Exit vmUtils.waitForOSState, rc: " +
        str(results['overallRC']))
    return results


def waitForVMState(rh, userid, desiredState, maxQueries=90, sleepSecs=5):
    """
    Wait for the virtual machine to go into the indicated state.

    Input:
       Request Handle
       userid whose state is to be monitored
       Desired state, 'on' or 'off', case sensitive
       Maximum attempts to wait for desired state before giving up
       Sleep duration between waits

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - RC returned from SMCLI if overallRC = 0.
          rs        - RS returned from SMCLI if overallRC = 0.

    Note:

    """

    rh.printSysLog("Enter vmUtils.waitForVMState, userid: " + userid +
                           " state: " + desiredState +
                           " maxWait: " + str(maxQueries) +
                           " sleepSecs: " + str(sleepSecs))

    results = {}
    maxQueries = int(maxQueries)

    cmd = ["sudo", "/sbin/vmcp", "query", "user", userid]
    strCmd = " ".join(cmd)
    stateFnd = False

    for i in range(1, maxQueries + 1):
        rh.printSysLog("Invoking: " + strCmd)
        try:
            out = subprocess.check_output(
                cmd,
                close_fds=True,
                stderr=subprocess.STDOUT)
            if isinstance(out, bytes):
                out = bytes.decode(out)

            rh.printSysLog("Query user output: " + out)

            if desiredState == 'on':
                stateFnd = True
                break
        except CalledProcessError as e:
            out = e.output
            if isinstance(out, bytes):
                out = bytes.decode(out)

            rh.printSysLog("Query user output: " + out)

            match = re.search('(^HCP\w\w\w045E|^HCP\w\w\w361E)', out)
            if match:
                # Logged off
                if desiredState == 'off':
                    stateFnd = True
                    break
            else:
                # Abnormal failure
                rh.printLn("ES", msgs.msg['0415'][1] % (modId, strCmd,
                    e.returncode, out))
                results = msgs.msg['0415'][0]
                results['rs'] = e.returncode
                break
        except Exception as e:
            # All other exceptions.
            rh.printLn("ES", msgs.msg['0421'][1] % (modId, strCmd,
                type(e).__name__, str(e)))
            results = msgs.msg['0421'][0]

        if i < maxQueries:
            # Sleep a bit before looping.
            time.sleep(sleepSecs)

    if stateFnd is True:
        results = {
                'overallRC': 0,
                'rc': 0,
                'rs': 0,
            }
    else:
        maxWait = maxQueries * sleepSecs
        rh.printLn("ES", msgs.msg['0414'][1] % (modId, userid,
            desiredState, maxWait))
        results = msgs.msg['0414'][0]

    rh.printSysLog("Exit vmUtils.waitForVMState, rc: " +
        str(results['overallRC']))
    return results


def purgeReader(rh):
    """
    Purge reader of the specified userid.

    Input:
       Request Handle

    Output:
       Dictionary containing the following:
          overallRC - overall return code, 0: success, non-zero: failure
          rc        - RC returned from SMCLI if overallRC = 0.
          rs        - RS returned from SMCLI if overallRC = 0.
          errno     - Errno returned from SMCLI if overallRC = 0.
          response  - Updated with an error message.

    Note:

    """
    rh.printSysLog("Enter vmUtils.purgeRDR, userid: " + rh.userid)
    results = {'overallRC': 0,
               'rc': 0,
               'rs': 0,
               'response': []}

    parms = ['-T', rh.userid, '-k', 'spoolids=all']

    results = invokeSMCLI(rh, "System_RDR_File_Manage", parms)

    if results['overallRC'] != 0:
        rh.printLn("ES", results['response'])
        rh.updateResults(results)

    rh.printSysLog("Exit vmUtils.purgeReader, rc: " +
                   str(results['overallRC']))
    return results
