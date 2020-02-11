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

import os
from six.moves import configparser


class Opt(object):
    def __init__(self, opt_name, section='default',
                 opt_type='str', help='',
                 default=None, required=False):
        self.name = opt_name
        self.section = section
        self.opt_type = opt_type
        self.default = default
        self.required = required
        self.help = help


zvm_opts = [
    # logging options
    Opt('log_dir',
        section='logging',
        default='/var/log/zvmsdk/',
        help='''
Directory where log file to be put into.

SDK has a set of logs to help administrator to debug
and aduit actions performed through SDK. Edit this option
if you want to put logs into specified place.

Please ensure the service running on the consume which
consumes SDK has the authorization to write to the path.
    '''),
    Opt('log_level',
        section='logging',
        default='logging.INFO',
        help='''
Level of the log.

SDK utilize python logging package to help admin debug
or analyze issues. it's recommend to set this value
to logging.DEBUG to get more detailed logs and set it to
logging.INFO(default) in normal situation.

recommend values:
logging.ERROR: level above ERROR will be written to log file.
logging.WARNINS: level above WARNING(ERROR, WARNING)
                 will be written to log file.
logging.INFO: level above INFO(ERROR, WARNING, INFO)
              will be written to log file.
logging.DEBUG: All log level (ERROR, WARNING, INFO, DEBUG)
               will be written to log file.
    '''),
    # zvm options
    Opt('default_nic_vdev',
        section='zvm',
        default='1000',
        help='''
Virtual device number for default NIC address.

This value is the first NIC virtual device number,
each NIC needs 3 numbers for control/read/write, so by default
the first NIC's address is 1000, the second one is 1003 etc.

Possible values:
    An integer value in hex format, between 0 and 65536 (x'FFFF').
    It should not conflict with other device numbers in the z/VM guest's
    configuration, for example device numbers of the root or ephemeral or
    persistent disks.

Sample NIC definitions in the z/VM user directory:
    NICDEF 1000 TYPE QDIO LAN SYSTEM <vswitch1> MACID <macid1>
    NICDEF 1003 TYPE QDIO LAN SYSTEM <vswitch2> MACID <macid2>
        '''
        ),
    Opt('default_admin_userid',
        section='zvm',
        help='''
Default LOGONBY userid(s) for the cloud.

This is a set of z/VM userid(s) which are allowed to logon using the LOGONBY
keyword to the guests created by the z/VM SDK solution, compatible with
the LBYONLY keyword of the user directory statement. This value is only used
when a guest is created. If you change this value, existing guests' directory
entries are not automatically updated with the new value.
When an ESM is installed, this parameter only governs when the ESM
defers to CP's processing.

Usage note:
    The default is an empty string (''). When the string is empty, you can't
    log on to your instances using the 3270 protocol; When a
    non-empty string is provided, blank chars will be used as delimiter,
    you can use LOGONBY xxx command to log on the guest using the corresponding
    admin userid's password.

    For example, when you set this value to 'oper1 oper2 oper3 jones', it means
    you can use any one of 'oper1', 'oper2', 'oper3', 'jones' as an admin user.

    see the z/VM CP Planning and Administration for additional information.

Possible values:
    A maximum of 8 blank-delimited strings. Each non-blank string must be a
    valid z/VM userid.
    e.g  '' is a valid value.
         'oper1 oper2' is a valid value.
         'o1 o2 o3 o4 o5 o6 o7 o8 o9' is NOT a valid value.
    '''),
    # FIXME: remove this option when switch to smt
    Opt('user_default_password',
        section='zvm'),
    Opt('disk_pool',
        section='zvm',
        required=True,
        help='''
zVM disk pool and type for root/ephemeral disks.

The option is combined by 2 parts and use : as separator.

The first part is the type of disks in the disk pool.
The disks in one disk pool must in same type (ECKD or FBA).
Possible values of the disk pool type:
    A string, either ECKD or FBA.

The second part is the volume group name defined in your directory manager
on your z/VM system, which will be used for allocating disks for
new guest. A dollar sign ($) is not allowed in the name.

Sample disk_pool values:
    ECKD:diskpo1
    FBA:testpool
    '''),
    Opt('user_profile',
        section='zvm',
        required=True,
        help='''
PROFILE name to use when creating a z/VM guest.

When SDK deploys an guest on z/VM, it can include some
common statements from a PROFILE definition.
This PROFILE must already be included in your z/VM user directory.

Possible values:
    An 8 character name of a PROFILE that is already defined in the z/VM
    user directory.
    '''),
    Opt('user_root_vdev',
        section='zvm',
        default='0100',
        help='''
Virtual device number for root disk.

When SDK deploys an guest, it creates a root disk and potentially
several data disks. This value is the virtual device number of the root
disk.

Possible values:
    An integer value in hex format, between 0 and 65536 (x'FFFF').
    It should not conflict with other device numbers in the z/VM guest's
    configuration, for example device numbers of the NICs or ephemeral or
    persistent disks.

Sample root disk in user directory:
    MDISK 0100 <disktype> <start> <end> <volumelabel> <readwrite>
'''),
    Opt('user_default_max_cpu',
        section='zvm',
        default=32,
        opt_type='int',
        help='''
The default maximum number of virtual processers the user can define.
This value is used as the default value for maximum vcpu number when
create a guest with no max_cpu specified.

The number must be a decimal value between 1 and 64.
'''),
    Opt('user_default_max_memory',
        section='zvm',
        default='64G',
        help='''
The default maximum size of memory the user can define.
This value is used as the default value for maximum memory size when
create a guest with no max_mem specified.
The value can be specified by 1-4 bits of number suffixed by either
M (Megabytes) or G (Gigabytes) and the number must be a whole number,
values such as 4096.8M or 32.5G are not supported.

The value should be adjusted based on your system capacity.
'''),
    Opt('namelist',
        section='zvm',
        help='''
The name of a list containing names of virtual servers to be queried. The list
which contains the userid list by default is named: VSMWORK1 NAMELIST, see
DMSSICNF COPY key: NameListFileIdAny. The list has to be accessible to the
SMAPI servers.

The length of namelist must no longer than 64.
'''),
    Opt('remotehost_sshd_port',
        section='zvm',
        default='22',
        help='''
The port number of remotehost sshd.
'''),
    Opt('temp_vdev_start',
        section='zvm',
        default='FF00',
        help='''
The starting vdev to use for temporary operations.
'''),
    Opt('temp_vdev_end',
        section='zvm',
        default='FF1F',
        help='''
The ending vdev to use for temporary operations.
'''),
    # image options
    Opt('sdk_image_repository',
        section='image',
        default='/var/lib/zvmsdk/images',
        help='''
Directory to store sdk images.

SDK image repository to store the imported images and the staging images that
is in snapshotting. Once snapshot finished, the image will be removed to the
netboot directory accordingly. Two kinds of image repository looks like:
/var/lib/zvmsdk/images/netboot/<image_osversion>/<imagename>
/var/lib/zvmsdk/images/staging/<image_osversion>/<imagename>
    '''),
    # file options
    Opt('file_repository',
        section='file',
        default='/var/lib/zvmsdk/files',
        help='''
Directory to store sdk imported or exported files.

SDK file repository to store the imported files and the files that will be
exported, the imported files will be put into <file_repository>/imported
the files to be exported will be put into <file_repository>/exported
    '''),
    # network options
    Opt('my_ip',
        section='network',
        required=True,
        help='''
IP address of the Linux machine which is running SDK on.

Some remote copy operations need to be performed during guest creation,
this option tell the SDK the host ip which can be used to perform copy
from and copy to operations.
    '''),
    # guest options
    Opt('console_log_size',
        section='guest',
        default=100,
        opt_type='int',
        help='''
The maximum allowed console log size, in kilobytes.

Console logs might be transferred to sdk user, this option controls how
large each file can be. A smaller size may mean more calls will be needed
to transfer large consoles, which may not be desirable for performance reasons.
    '''),
    Opt('softstop_timeout',
        section='guest',
        default=60,
        opt_type='int',
        help='''
The maximum time waiting until the guest shut down.

Sometimes, the shutdown action will take a bit lone time to complete.
If you want to make sure the guest in shut-down status after executing action
of softstop, this will help.
    '''),
    Opt('softstop_interval',
        section='guest',
        default=5,
        opt_type='int',
        help='''
The interval time between 2 retries, in seconds.

This will take effect only when you set softstop_retries item.
What's more, the value of softstop_timeout/softstop_interval is
the times retried.
    '''),
    # monitor options
    Opt('cache_interval',
        section='monitor',
        default=300,
        opt_type='int',
        help='''
Cached monitor data update interval

This is used to prevent excessive effort spent retrieving the
monitor data by calling the SDK backend utilities. When this cache
is enabled, a inspect call will only call the SDK backend utilities
when the inspected guest's info does not exist in the cache or
when the cache data is expired. And when an cache update is needed,
all the existing guests' data will be retrieved in a single call to
the backend.

When this value is below or equal to zero, the cache
will be disabled and each inspect call will need to call the backend
utilities to get the inspected guest's monitor data.
        '''
        ),
    # wsgi options
    # this option is used when sending http request
    # to sdk wsgi, default to none so no token validation
    # will be used.
    Opt('auth',
        section='wsgi',
        default='none',
        opt_type='str',
        help='''
Whether auth will be used.

When sending http request from outside to running zvmsdk,
Client will be requested to input username/password in order
to authorize the call.
Set this to 'none' indicated no auth will be used and 'auth'
means username and password need to be specified.

Possible value:
'none': no auth will be required
'auth': need auth, currently pyjwt is used to return a token
        to caller if the username and password is correct.
''',
        ),
    Opt('token_validation_period',
        section='wsgi',
        default=3600,
        opt_type='int',
        help='''
How long the token is valid.

If a token auth is used, the token return to user will be
expired after the period passed. This ensure an user who
get this token will not be authorized all the time, a new
token need to be recreated after certain time period.
''',
        ),
    Opt('token_path',
        section='wsgi',
        default='/etc/zvmsdk/token.dat',
        opt_type='str',
        help='''
file path that contains admin-token to access sdk http server.

Admin-token in order to get a user-token from zvm sdk, and the user-token
will be used to validate request before user-token expire.
'''
        ),
    Opt('max_concurrent_deploy_capture',
        section='wsgi',
        default=20,
        opt_type='int',
        help='''
The max total number of concurrent deploy and capture requests allowed in a
single z/VM Cloud Connector process.

If more requests than this value are revieved concurrently, the z/VM Cloud
Connector would reject the requests and return error to avoid resource
exhaustion.
.
'''
        ),
    # Daemon server options
    Opt('bind_addr',
        section='sdkserver',
        default='127.0.0.1',
        opt_type='str',
        help='''
The IP address that the SDK server is listen on.

When the SDK server deamon starts, it will try to bind to
this address and port bind_port, and wait for the SDK client
connection to handle API request.
'''
        ),
    Opt('bind_port',
        section='sdkserver',
        opt_type='int',
        default=2000,
        help='''
The port that the SDK server is listen on.

This will work as a pair with bind_addr when the SDK server daemon
starts, more info can be found in that configuration description.
'''
        ),
    Opt('request_queue_size',
        section='sdkserver',
        opt_type='int',
        default=128,
        help='''
The size of request queue in SDK server.

SDK server maintains a queue to keep all the accepted but not handled requests,
and the SDK server workers fetch requests from this queue.
To some extend, this queue size decides the max socket opened in SDK server.
This value should be adjusted according to the system resource.
'''
        ),
    Opt('max_worker_count',
        section='sdkserver',
        opt_type='int',
        default=64,
        help='''
The maximum number of worker thread in SDK server to handle client requests.

These worker threads would work concurrently to handle requests from client.
This value should be adjusted according to the system resource and workload.
'''
        ),
    # database options
    Opt('dir',
        section='database',
        default='/var/lib/zvmsdk/databases/',
        opt_type='str',
        help='''
Directory to store database.

SDK databases are used to store a set of tables which contain the
information of network, volume, image, etc. This option is used to
tell SDK where to store the database files, make sure the process
running SDK is able to read write and execute the directory.
'''
        ),
    # volume options
    Opt('fcp_list',
        section='volume',
        default='',
        opt_type='str',
        help='''
volume fcp list.

SDK will only use the fcp devices in the scope of this value.
'''),
    # tests options
    Opt('images',
        section='tests',
        opt_type='str',
        ),
    Opt('userid_prefix',
        section='tests',
        default='tst',
        opt_type='str',
        ),
    Opt('ip_addr_list',
        section='tests',
        default='192.168.0.2 192.168.0.3 192.168.0.4 192.168.0.5 192.168.0.6',
        opt_type='str',
        ),
    Opt('vswitch',
        section='tests',
        opt_type='str',
        ),
    Opt('gateway_v4',
        section='tests'),
    Opt('cidr',
        section='tests'),
    Opt('restapi_url',
        section='tests',
        default='http://127.0.0.1:8888'),
    Opt('zvm_fcp',
        section='tests'),
    Opt('target_wwpn',
        section='tests'),
    Opt('target_lun',
        section='tests'),
    Opt('mount_point',
        section='tests'),
    ]


class ConfigOpts(object):

    def __init__(self):
        self.dicts = {}

    def get_config_dicts_default(self, opts):
        _dict = {}
        for opt in opts:
            sec = opt.section
            if _dict.get(sec) is None:
                _dict[sec] = {}
            _dict[sec][opt.name] = {'required': opt.required,
                                    'default': opt.default,
                                    'type': opt.opt_type,
                                    'help': opt.help}
        return _dict

    def register(self, opts):
        # Register the defined options and parse to dict
        self.dicts = self.get_config_dicts_default(opts)
        return self.clear_and_to_dict()

    def config(self):
        # Load config file and merge with default definitions
        # read config file
        override_dicts = self.read_config_file_to_dicts()
        # overwrite default value
        try:
            self.dicts = self.merge(self.dicts, override_dicts)
        except ImportError:
            pass
        # Check config value
        self._check_value(self.dicts)
        # Clear unused attributes of each option, and parse to our defined dict
        return self.clear_and_to_dict()

    def read_config_file_to_dicts(self):
        configs = {}
        read_file = self.find_config_file(project="zvmsdk")
        if read_file is None:
            raise ConfFileMissingError()
        else:
            cf = configparser.ConfigParser()
            cf.read(read_file)
            # read each section and option to dict
            secs = cf.sections()
            for sec in secs:
                configs[sec] = {}
                # get all options of the section in a list
                opts = cf.options(sec)
                for opt in opts:
                    val = cf.get(sec, opt)
                    configs[sec][opt] = val
            return configs

    def merge(self, defaults, override):
        # merge the defaults and overridden
        # The overridden options would only have 'default' set in the
        # resulted dicts
        r = {}
        for k, v in defaults.items():
            if k in override:
                if isinstance(v, dict) and isinstance(override[k], dict):
                    r[k] = self.merge(v, override[k])
                elif isinstance(v, dict):
                    if override[k] is not None:
                        v['default'] = override[k]
                    r[k] = v
                else:
                    r[k] = override[k]
            else:
                r[k] = v
        return r

    def clear_and_to_dict(self):
        # This function would clear the dict to remove the unused keys
        # ('required', 'default', 'type', 'help'), set the opt value to
        # the final value merged in 'default'.
        # And then, convert the python dict to our defined Dict object
        clear_dict = {}
        pydict = self.dicts
        for k1, v1 in pydict.items():
            r_con = {}
            for k2, v2 in v1.items():
                r_con[k2] = v2['default']
            clear_dict[k1] = r_con

        return self.toDict(clear_dict)

    def _check_value(self, conf):
        for k1, v1 in conf.items():
            for k2, v2 in v1.items():
                # Check required options
                if v2['required'] and (v2['default'] is None):
                    raise RequiredOptMissingError(k1, k2)
                # Convert type
                if v2['type'] == 'int':
                    v2['default'] = int(v2['default'])
                # Check format
                if (k2 == "disk_pool") and (v2['default'] is not None):
                    self._check_zvm_disk_pool(v2['default'])
                # check user_default_max_memory
                if (k2 == "user_default_max_memory") and (
                    v2['default'] is not None):
                    self._check_user_default_max_memory(v2['default'])
                # check user_default_max_cpu
                if (k2 == "user_default_max_cpu") and (
                    v2['default'] is not None):
                    self._check_user_default_max_cpu(v2['default'])

    def _check_zvm_disk_pool(self, value):
        disks = value.split(':')
        if (len(disks) != 2) or (disks[0].upper() not in ['FBA', 'ECKD']) or (
            disks[1] == ''):
            raise OptFormatError("zvm", "disk_pool", value)

    def _check_user_default_max_memory(self, value):
        suffix = value[-1].upper()
        size = value[:-1]
        if (suffix not in ['G', 'M']) or (len(size) > 4) or (
            size.strip('0123456789') != ''):
            raise OptFormatError("zvm", "user_default_max_memory", value)

    def _check_user_default_max_cpu(self, value):
        if (value < 1) or (value > 64):
            raise OptFormatError("zvm", "user_default_max_cpu", value)

    def toDict(self, d):
        D = Dict()
        for k, v in d.items():
            D[k] = self.toDict(v) if isinstance(v, dict) else v
        return D

    def _fixpath(self, p):
        """Apply tilde expansion and absolutization to a path."""
        return os.path.abspath(os.path.expanduser(p))

    def _get_config_dirs(self):
        """Return a list of directories where config files may be located.

        following directories are returned::

          ./
          ../etc
          ~/
          /etc/zvmsdk/
        """
        _cwd = os.path.split(os.path.abspath(__file__))[0]
        _pdir = os.path.split(_cwd)[0]
        _etcdir = ''.join((_pdir, '/', 'etc/'))
        cfg_dirs = [
            self._fixpath(_cwd),
            self._fixpath('/etc/zvmsdk/'),
            self._fixpath('/etc/'),
            self._fixpath('~'),
            self._fixpath(_etcdir),
        ]
        return [x for x in cfg_dirs if x]

    def _search_dirs(self, dirs, basename, extension=""):
        """Search a list of directories for a given filename or directory name.

        Iterator over the supplied directories, returning the first file
        found with the supplied name and extension.

        :param dirs: a list of directories
        :param basename: the filename
        :param extension: the file extension, for example '.conf'
        :returns: the path to a matching file, or None
        """
        for d in dirs:
            path = os.path.join(d, '%s%s' % (basename, extension))
            if os.path.exists(path):
                return path

        return None

    def find_config_file(self, project=None, extension='.conf'):
        """Return the config file.

        :param project: "zvmsdk"
        :param extension: the type of the config file

        """
        cfg_dirs = self._get_config_dirs()
        config_files = self._search_dirs(cfg_dirs, project, extension)

        return config_files


class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'CONF' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


class RequiredOptMissingError(Exception):
    """Raised if an option is required but no value is supplied by the user."""

    def __init__(self, grp_name, opt_name):
        self.grp_name = grp_name
        self.opt_name = opt_name

    def __str__(self):
        return "value required for option %s - %s" % (self.grp_name,
                                                      self.opt_name)


class ConfFileMissingError(Exception):
    """Raised if the configuration file zvmsdk.conf cann't be found."""

    def __init__(self):
        message = "zvmsdk.conf is not found."
        super(ConfFileMissingError, self).__init__(message)


class OptFormatError(Exception):
    """Raised if an option is required but no value is supplied by the user."""

    def __init__(self, grp_name, opt_name, value):
        self.grp_name = grp_name
        self.opt_name = opt_name
        self.value = value

    def __str__(self):
        return "value %s for option  %s - %s is invalid" % (self.value,
                                                            self.grp_name,
                                                            self.opt_name)


CONFOPTS = ConfigOpts()
CONF = CONFOPTS.register(zvm_opts)


def load_config():
    global CONF
    CONF = CONFOPTS.config()
