# Request Handle for Systems Management Ultra Thin Layer
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

import logging
import logging.handlers
import shlex
from six import string_types

from smtLayer import changeVM
from smtLayer import cmdVM
from smtLayer import deleteVM
from smtLayer import getHost
from smtLayer import getVM
from smtLayer import makeVM
from smtLayer import migrateVM
from smtLayer import msgs
from smtLayer import smapi
from smtLayer import powerVM

from zvmsdk import log as zvmsdklog


modId = "RQH"
version = '1.0.0'         # Version of this script


class ReqHandle(object):
    """
    Systems Management Ultra Thin Layer Request Handle.
    This class contains all information related to a specific request.
    All functions are passed this request handle.
    """

    funcHandler = {
        'CHANGEVM': [
            lambda rh: changeVM.showInvLines(rh),
            lambda rh: changeVM.showOperandLines(rh),
            lambda rh: changeVM.parseCmdline(rh),
            lambda rh: changeVM.doIt(rh)],
        'CMDVM': [
            lambda rh: cmdVM.showInvLines(rh),
            lambda rh: cmdVM.showOperandLines(rh),
            lambda rh: cmdVM.parseCmdline(rh),
            lambda rh: cmdVM.doIt(rh)],
        'DELETEVM': [
            lambda rh: deleteVM.showInvLines(rh),
            lambda rh: deleteVM.showOperandLines(rh),
            lambda rh: deleteVM.parseCmdline(rh),
            lambda rh: deleteVM.doIt(rh)],
        'GETHOST': [
            lambda rh: getHost.showInvLines(rh),
            lambda rh: getHost.showOperandLines(rh),
            lambda rh: getHost.parseCmdline(rh),
            lambda rh: getHost.doIt(rh)],
        'GETVM': [
            lambda rh: getVM.showInvLines(rh),
            lambda rh: getVM.showOperandLines(rh),
            lambda rh: getVM.parseCmdline(rh),
            lambda rh: getVM.doIt(rh)],
        'MAKEVM': [
            lambda rh: makeVM.showInvLines(rh),
            lambda rh: makeVM.showOperandLines(rh),
            lambda rh: makeVM.parseCmdline(rh),
            lambda rh: makeVM.doIt(rh)],
        'MIGRATEVM': [
            lambda rh: migrateVM.showInvLines(rh),
            lambda rh: migrateVM.showOperandLines(rh),
            lambda rh: migrateVM.parseCmdline(rh),
            lambda rh: migrateVM.doIt(rh)],
        'POWERVM': [
            lambda rh: powerVM.showInvLines(rh),
            lambda rh: powerVM.showOperandLines(rh),
            lambda rh: powerVM.parseCmdline(rh),
            lambda rh: powerVM.doIt(rh)],
        'SMAPI': [
            lambda rh: smapi.showInvLines(rh),
            lambda rh: smapi.showOperandLines(rh),
            lambda rh: smapi.parseCmdline(rh),
            lambda rh: smapi.doIt(rh)],
    }

    def __init__(self, **kwArgs):
        """
        Constructor

        Input:
           captureLogs=<True|False>
                            Enables or disables log capture for all requests.
           cmdName=<cmdName>
                            Name of the command that is using ReqHandle.
                            This is only used for the function help.
                            It defaults to "smtCmd.py".
           requestId=requestId
                            Optional request Id
           smt=<smtDaemon>
                            SMT daemon, it it exists.
        """

        self.results = {
            'overallRC': 0,       # Overall return code for the function, e.g.
                                  #   0  - Everything went ok
                                  #   2  - Something in the IUCVCLNT failed
                                  #   3  - Something in a local vmcp failed
                                  #   4  - Input validation error
                                  #   5  - Miscellaneous processing error
                                  #   8  - SMCLI - SMAPI failure
                                  #   24 - SMCLI - Parsing failure
                                  #   25 - SMCLI - Internal Processing Error
                                  #   99 - Unexpected failure
            'rc': 0,              # Return code causing the return
            'rs': 0,              # Reason code causing the return
            'errno': 0,           # Errno value causing the return
            'strError': '',       # Error as a string value.
                                  #   Normally, this is the errno description.
            'response': [],       # Response strings
            'logEntries': [],     # Syslog entries related to this request
            }

        if 'smt' in kwArgs.keys():
            self.daemon = kwArgs['smt']    # SMT Daemon
            # Actual SysLog handling is done in SMT.
        else:
            self.daemon = ''
            # Set up SysLog handling to be done by ReqHandle
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.DEBUG)
            self.handler = logging.handlers.SysLogHandler(address = '/dev/log')
            self.formatter = (
                logging.Formatter('%(module)s.%(funcName)s: %(message)s'))
            self.handler.setFormatter(self.formatter)
            self.logger.addHandler(self.handler)

        if 'cmdName' in kwArgs.keys():
            self.cmdName = kwArgs['cmdName']
        else:
            self.cmdName = 'smtCmd.py'

        if 'requestId' in kwArgs.keys():
            self.requestId = kwArgs['requestId']
        else:
            self.requestId = 'REQ_' + hex(id(self))[2:]
            # <todo>  Need to generate a default request Id

        self.function = ''            # Function being processed
        self.subfunction = ''         # Subfunction be processed (optional)
        self.userid = ''              # Target userid
        self.parms = {}               # Dictionary of additional parms
        self.argPos = 0               # Prep to parse first command line arg

        # Capture & return Syslog entries
        if 'captureLogs' in kwArgs.keys():
            self.captureLogs = kwArgs['captureLogs']
        else:
            self.captureLogs = False

    def driveFunction(self):
        """
        Drive the function/subfunction call.

        Input:
           Self with request filled in.

        Output:
           Request Handle updated with the results.
           Overall return code - 0: successful, non-zero: error
        """

        if self.function == 'HELP':
            # General help for all functions.
            self.printLn("N", "")
            self.printLn("N", "Usage:")
            self.printLn("N", "  python " + self.cmdName + " --help")
            for key in sorted(ReqHandle.funcHandler):
                ReqHandle.funcHandler[key][0](self)
            self.printLn("N", "")
            self.printLn("N", "Operand(s):")
            for key in sorted(ReqHandle.funcHandler):
                ReqHandle.funcHandler[key][1](self)
            self.printLn("N", "")
            self.updateResults({}, reset=1)
        elif self.function == 'VERSION':
            # Version of ReqHandle.
            self.printLn("N", "Version: " + version)
            self.updateResults({}, reset=1)
        else:
            # Some type of function/subfunction invocation.
            if self.function in self.funcHandler:
                # Invoke the functions doIt routine to route to the
                # appropriate subfunction.
                self.funcHandler[self.function][3](self)
            else:
                # Unrecognized function
                msg = msgs.msg['0007'][1] % (modId, self.function)
                self.printLn("ES", msg)
                self.updateResults(msgs.msg['0007'][0])

        return self.results

    def parseCmdline(self, requestData):
        """
        Parse the request command string.

        Input:
           Self with request filled in.

        Output:
           Request Handle updated with the parsed information so that
              it is accessible via key/value pairs for later processing.
           Return code - 0: successful, non-zero: error
        """

        self.printSysLog("Enter ReqHandle.parseCmdline")

        # Save the request data based on the type of operand.
        if isinstance(requestData, list):
            self.requestString = ' '.join(requestData)  # Request as a string
            self.request = requestData                  # Request as a list
        elif isinstance(requestData, string_types):
            self.requestString = requestData            # Request as a string
            self.request = shlex.split(requestData)     # Request as a list
        else:
            # Request data type is not supported.
            msg = msgs.msg['0012'][1] % (modId, type(requestData))
            self.printLn("ES", msg)
            self.updateResults(msgs.msg['0012'][0])
            return self.results
        self.totalParms = len(self.request)   # Number of parms in the cmd

        # Handle the request, parse it or return an error.
        if self.totalParms == 0:
            # Too few arguments.
            msg = msgs.msg['0009'][1] % modId
            self.printLn("ES", msg)
            self.updateResults(msgs.msg['0009'][0])
        elif self.totalParms == 1:
            self.function = self.request[0].upper()
            if self.function == 'HELP' or self.function == 'VERSION':
                pass
            else:
                # Function is not HELP or VERSION.
                msg = msgs.msg['0008'][1] % (modId, self.function)
                self.printLn("ES", msg)
                self.updateResults(msgs.msg['0008'][0])
        else:
            # Process based on the function operand.
            self.function = self.request[0].upper()
            if self.request[0] == 'HELP' or self.request[0] == 'VERSION':
                pass
            else:
                # Handle the function related parms by calling the function
                # parser.
                if self.function in ReqHandle.funcHandler:
                    self.funcHandler[self.function][2](self)
                else:
                    # Unrecognized function
                    msg = msgs.msg['0007'][1] % (modId, self.function)
                    self.printLn("ES", msg)
                    self.updateResults(msgs.msg['0007'][0])

        self.printSysLog("Exit ReqHandle.parseCmdline, rc: " +
                         str(self.results['overallRC']))
        return self.results

    def printLn(self, respType, respString):
        """
        Add one or lines of output to the response list.

        Input:
           Response type: One or more characters indicate type of response.
              E - Error message
              N - Normal message
              S - Output should be logged
              W - Warning message
        """

        if 'E' in respType:
            respString = '(Error) ' + respString
        if 'W' in respType:
            respString = '(Warning) ' + respString
        if 'S' in respType:
            self.printSysLog(respString)
        self.results['response'] = (self.results['response'] +
                                   respString.splitlines())
        return

    def printSysLog(self, logString):
        """
        Log one or more lines.  Optionally, add them to logEntries list.

        Input:
           Strings to be logged.
        """

        if self.daemon:
            self.daemon.logger.debug(self.requestId + ": " + logString)
        elif zvmsdklog.LOGGER.getloglevel() <= logging.DEBUG:
            # print log only when debug is enabled
            if self.daemon == '':
                self.logger.debug(self.requestId + ": " + logString)

        if self.captureLogs is True:
            self.results['logEntries'].append(self.requestId + ": " +
                logString)
        return

    def printSysLogForDebug(self, logString):
        """
        Log one or more lines.  Optionally, add them to logEntries list.

        Input:
           Strings to be logged.
        """

        if self.daemon:
            self.daemon.logger.debug(self.requestId + ": " + logString)
        else:
            self.logger.debug(self.requestId + ": " + logString)

        if self.captureLogs is True:
            self.results['logEntries'].append(self.requestId + ": " +
                logString)
        return

    def updateResults(self, newResults, **kwArgs):
        """
        Update the results related to this request excluding the 'response'
        and 'logEntries' values.
        We specifically update (if present):
           overallRC, rc, rs, errno.

        Input:
           Dictionary containing the results to be updated or an empty
              dictionary the reset keyword was specified.
           Reset keyword:
              0 - Not a reset.  This is the default is reset keyword was not
                  specified.
              1 - Reset failure related items in the result dictionary.
                  This exclude responses and log entries.
              2 - Reset all result items in the result dictionary.

        Output:
           Request handle is updated with the results.
        """

        if 'reset' in kwArgs.keys():
            reset = kwArgs['reset']
        else:
            reset = 0

        if reset == 0:
            # Not a reset.  Set the keys from the provided dictionary.
            for key in newResults.keys():
                if key == 'response' or key == 'logEntries':
                    continue
                self.results[key] = newResults[key]
        elif reset == 1:
            # Reset all failure related items.
            self.results['overallRC'] = 0
            self.results['rc'] = 0
            self.results['rs'] = 0
            self.results['errno'] = 0
            self.results['strError'] = ''
        elif reset == 2:
            # Reset all results information including any responses and
            # log entries.
            self.results['overallRC'] = 0
            self.results['rc'] = 0
            self.results['rs'] = 0
            self.results['errno'] = 0
            self.results['strError'] = ''
            self.results['logEntries'] = ''
            self.results['response'] = ''

        return
