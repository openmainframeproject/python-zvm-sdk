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


import json
import six
import socket
import sys
import threading
import traceback

from zvmsdk import api
from zvmsdk import config
from zvmsdk import exception
from zvmsdk import log
from zvmsdk import returncode
from zvmsdk import smtclient

if six.PY3:
    import queue as Queue
else:
    import Queue


CONF = config.CONF
LOG = log.LOG


def init():
    # init PERSMAPI, note even the PERSMAPI is up running
    # we can safely ignore the error (0/8)
    # the logs can be found at /var/log/zvmsdk/smt.log
    st = smtclient.get_smtclient()
    st.guest_start('PERSMAPI')


class SDKServer(object):
    def __init__(self):
        # Initailize SDK API
        self.sdkapi = api.SDKAPI()
        self.server_socket = None
        self.request_queue = Queue.Queue(maxsize=
                                         CONF.sdkserver.request_queue_size)
        init()

    def log_error(self, msg):
        thread = threading.current_thread().name
        msg = ("[%s] %s" % (thread, msg))
        LOG.error(msg)

    def log_info(self, msg):
        thread = threading.current_thread().name
        msg = ("[%s] %s" % (thread, msg))
        LOG.info(msg)

    def log_warn(self, msg):
        thread = threading.current_thread().name
        msg = ("[%s] %s" % (thread, msg))
        LOG.warning(msg)

    def log_debug(self, msg):
        thread = threading.current_thread().name
        msg = ("[%s] %s" % (thread, msg))
        LOG.debug(msg)

    def construct_internal_error(self, msg):
        self.log_error(msg)
        error = returncode.errors['internal']
        results = error[0]
        results['modID'] = returncode.ModRCs['sdkserver']
        results.update({'rs': 1,
                        'errmsg': error[1][1] % {'msg': msg},
                        'output': ''})
        return results

    def construct_api_name_error(self, msg):
        self.log_error(msg)
        error = returncode.errors['API']
        results = error[0]
        results['modID'] = returncode.ModRCs['sdkserver']
        results.update({'rs': 1,
                        'errmsg': error[1][1] % {'msg': msg},
                        'output': ''})
        return results

    def send_results(self, client, addr, results):
        """ send back results to client in the json format of:
        {'overallRC': x, 'modID': x, 'rc': x, 'rs': x, 'errmsg': 'msg',
         'output': 'out'}
        """
        json_results = json.dumps(results)
        json_results = json_results.encode()

        sent = 0
        total_len = len(json_results)
        got_error = False
        while (sent < total_len):
            this_sent = client.send(json_results[sent:])
            if this_sent == 0:
                got_error = True
                break
            sent += this_sent
        if got_error or sent != total_len:
            self.log_error("(%s:%s) Failed to send back results to client, "
                           "results: %s" % (addr[0], addr[1], json_results))
        else:
            self.log_debug("(%s:%s) Results sent back to client successfully."
                           % (addr[0], addr[1]))

    def serve_API(self, client, addr):
        """ Read client request and call target SDK API"""
        self.log_debug("(%s:%s) Handling new request from client." %
                       (addr[0], addr[1]))
        results = None
        try:
            data = client.recv(4096)
            data = bytes.decode(data)
            # When client failed to send the data or quit before sending the
            # data, server side would receive null data.
            # In such case, server would not send back any info and just
            # terminate this thread.
            if not data:
                self.log_warn("(%s:%s) Failed to receive data from client." %
                              (addr[0], addr[1]))
                return
            api_data = json.loads(data)

            # API_data should be in the form [funcname, args_list, kwargs_dict]
            if not isinstance(api_data, list) or len(api_data) != 3:
                msg = ("(%s:%s) SDK server got wrong input: '%s' from client."
                       % (addr[0], addr[1], data))
                results = self.construct_internal_error(msg)
                return

            # Check called API is supported by SDK
            (func_name, api_args, api_kwargs) = api_data
            self.log_debug("(%s:%s) Request func: %s, args: %s, kwargs: %s" %
                           (addr[0], addr[1], func_name, str(api_args),
                            str(api_kwargs)))
            try:
                api_func = getattr(self.sdkapi, func_name)
            except AttributeError:
                msg = ("(%s:%s) SDK server got wrong API name: %s from"
                       "client." % (addr[0], addr[1], func_name))
                results = self.construct_api_name_error(msg)
                return

            # invoke target API function
            return_data = api_func(*api_args, **api_kwargs)
        except exception.SDKBaseException as e:
            self.log_error("(%s:%s) %s" % (addr[0], addr[1],
                                           traceback.format_exc()))
            # get the error info from exception attribute
            # All SDKbaseexception should eventually has a
            # results attribute defined which can be used by
            # sdkserver here
            if e.results is None:
                msg = ("(%s:%s) SDK server got exception without results "
                       "defined, error: %s" % (addr[0], addr[1],
                                               e.format_message()))
                results = self.construct_internal_error(msg)
            else:
                results = {'overallRC': e.results['overallRC'],
                           'modID': e.results['modID'],
                           'rc': e.results['rc'],
                           'rs': e.results['rs'],
                           'errmsg': e.format_message(),
                           'output': ''}
        except Exception as e:
            self.log_error("(%s:%s) %s" % (addr[0], addr[1],
                                           traceback.format_exc()))
            msg = ("(%s:%s) SDK server got unexpected exception: "
                   "%s" % (addr[0], addr[1], repr(e)))
            results = self.construct_internal_error(msg)
        else:
            if return_data is None:
                return_data = ''
            results = {'overallRC': 0, 'modID': None,
                       'rc': 0, 'rs': 0,
                       'errmsg': '',
                       'output': return_data}
        # Send back the final results
        try:
            if results is not None:
                self.send_results(client, addr, results)
        except Exception as e:
            # This should not happen in normal case.
            # A special case is the server side socket is closed/removed
            # before the send() action.
            self.log_error("(%s:%s) %s" % (addr[0], addr[1], repr(e)))
        finally:
            # Close the connection to make sure the thread socket got
            # closed even when it got unexpected exceptions.
            self.log_debug("(%s:%s) Finish handling request, closing "
                           "socket." % (addr[0], addr[1]))
            client.close()

    def worker_loop(self):
        # The worker thread would continuously fetch request from queue
        # in a while loop.
        while True:
            try:
                # This get() function raise Empty exception when there's no
                # available item in queue
                clt_socket, clt_addr = self.request_queue.get(block=False)
            except Queue.Empty:
                self.log_debug("No more item in request queue, worker will "
                               "exit now.")
                break
            except Exception as err:
                self.log_error("Failed to get request item from queue, error: "
                               "%s. Worker will exit now." % repr(err))
                break
            else:
                self.serve_API(clt_socket, clt_addr)
                self.request_queue.task_done()

    def setup(self):
        # create server socket
        try:
            self.server_socket = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
        except socket.error as msg:
            self.log_error("Failed to create SDK server socket: %s" % msg)
            sys.exit(1)

        server_sock = self.server_socket
        # bind server address and port
        host = CONF.sdkserver.bind_addr
        port = CONF.sdkserver.bind_port
        try:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((host, port))
        except socket.error as msg:
            self.log_error("Failed to bind to (%s, %d), reason: %s" %
                             (host, port, msg))
            server_sock.close()
            sys.exit(1)

        # Start listening
        server_sock.listen(5)
        self.log_info("SDK server now listening")

    def run(self):
        # Keep running in a loop to handle client connections
        while True:
            # Wait client connection
            conn, addr = self.server_socket.accept()
            self.log_debug("(%s:%s) Client connected." % (addr[0],
                                                           addr[1]))
            # This put() function would be blocked here until there's
            # a slot in the queue
            self.request_queue.put((conn, addr))
            thread_count = threading.active_count()
            if thread_count <= CONF.sdkserver.max_worker_count:
                thread = threading.Thread(target=self.worker_loop)
                self.log_debug("Worker count: %d, starting new worker: %s" %
                               (thread_count - 1, thread.name))
                thread.start()


def start_daemon():
    server = SDKServer()
    try:
        server.setup()
        server.run()
    finally:
        # This finally won't catch exceptions from child thread, so
        # the close here is safe.
        if server.server_socket is not None:
            server.log_info("Closing the server socket.")
            server.server_socket.close()
