"""
Sample code that invokes SDKAPI.
"""

import os
import time

from zvmsdk import api


# Guest properties
GUEST_USERID = 'SDKSAMP1'
GUEST_PROFILE = 'osdflt'
GUEST_VCPUS = 1
GUEST_MEMORY = 1024         # in megabytes
GUEST_ROOT_DISK_SIZE = 1    # in gigabytes
DISK_POOL = 'ECKD:xcateckd'

# Image properties
IMAGE_PATH = '/root/smuttest/rhel67eckd_small_1100cyl.img'
IMAGE_OS_VERSION = 'rhel6.7'

# Network properties
GUEST_IP_ADDR = '192.168.95.200'
GATEWAY = '192.168.95.1'
CIDR = '192.168.95.0/24'
VSWITCH_NAME = 'xcatvsw2'


sdkapi = api.SDKAPI()


def terminate_guest(userid):
    """Destroy a virtual machine.

    Input parameters:
    :userid:   USERID of the guest, last 8 if length > 8
    """
    sdkapi.guest_delete(userid)


def describe_guest(userid):
    """Get virtual machine basic information.

    Input parameters:
    :userid:   USERID of the guest, last 8 if length > 8
    """

    inst_info = sdkapi.guest_get_info(userid)
    return inst_info


def start_guest(userid):
    """Power on a virtual machine.

    Input parameters:
    :userid:   USERID of the guest, last 8 if length > 8
    """
    sdkapi.guest_start(userid)


def stop_guest(userid):
    """Shutdown a virtual machine.

    Input parameters:
    :userid:   USERID of the guest, last 8 if length > 8
    """
    sdkapi.guest_start(userid)


def capture_guest(userid):
    """Caputre a virtual machine image.

    Input parameters:
    :userid:   USERID of the guest, last 8 if length > 8

    Output parameters:
    :image_name:      Image name that defined in xCAT image repo
    """
    # TODO: check power state ,if down ,start

    # do capture
    pass


def import_image(image_path, os_version):
    """Import image.

    Input parameters:
    :image_path:      Image file path
    :os_version:      Operating system version. e.g. rhel7.2
    """
    image_name = os.path.basename(image_path)
    print("Checking if image %s exists or not, import it if not exists" %
          image_name)
    image_info = sdkapi.image_query(image_name)
    if not image_info:
        print("Importing image %s ..." % image_name)
        url = 'file://' + image_path
        sdkapi.image_import(image_name, url, {'os_version': os_version})
    else:
        print("Image %s already exists" % image_name)


def delete_image(image_name):
    """Delete image.

    Input parameters:
    :image_name:      Image name that defined in xCAT image repo
    """
    pass


def _run_guest(userid, image_path, os_version, profile,
                 cpu, memory, network_info, disks_list):
    """Deploy and provision a virtual machine.

    Input parameters:
    :userid:            USERID of the guest, no more than 8.
    :image_name:        path of the image file
    :os_version:        os version of the image file
    :profile:           profile of the userid
    :cpu:               the number of vcpus
    :memory:            memory
    :network_info:      dict of network info.members:
        :ip_addr:           ip address of vm
        :gateway:           gateway of net
        :vswitch_name:      switch name
        :cidr:              CIDR
    :disks_list:            list of disks to add.eg:
        disks_list = [{'size': '3g',
                       'is_boot_disk': True,
                       'disk_pool': 'ECKD:xcateckd'}]
    """
    # Import image if not exists
    import_image(image_path, os_version)

    # Start time
    spawn_start = time.time()

    # Create userid
    print("Creating userid %s ..." % userid)
    sdkapi.guest_create(userid, cpu, memory, disks_list, profile)

    # Deploy image to root disk
    image_name = os.path.basename(image_path)
    print("Deploying %s to %s ..." % (image_name, userid))
    sdkapi.guest_deploy(userid, image_name)

    # Create network device and configure network interface
    print("Configuring network interface for %s ..." % userid)
    sdkapi.guest_create_network_interface(userid, os_version, [network_info],
                                          True)
    sdkapi.guest_nic_couple_to_vswitch(userid, '1000',
                                       network_info['vswitch_name'])
    sdkapi.vswitch_grant_user(network_info['vswitch_name'], userid)

    # Setup IUCV channel
    print("Configuring IUCV channel for %s ..." % userid)
    sdkapi.guest_authorize_iucv_client(userid)

    # Power on the vm
    print("Starting guest %s" % userid)
    sdkapi.guest_start(userid)

    # End time
    spawn_time = time.time() - spawn_start
    print "Instance-%s pawned succeeded in %s seconds" % (userid, spawn_time)


def run_guest():
    """ A sample for quick deploy and start a virtual guest."""
    global GUEST_USERID
    global GUEST_PROFILE
    global GUEST_VCPUS
    global GUEST_MEMORY
    global GUEST_ROOT_DISK_SIZE
    global DISK_POOL
    global IMAGE_PATH
    global IMAGE_OS_VERSION
    global GUEST_IP_ADDR
    global GATEWAY
    global CIDR
    global VSWITCH_NAME

    network_info = {'ip_addr': GUEST_IP_ADDR,
         'gateway_addr': GATEWAY,
         'cidr': CIDR,
         'vswitch_name': VSWITCH_NAME}
    disks_list = [{'size': '%ig' % GUEST_ROOT_DISK_SIZE,
                   'is_boot_disk': True,
                   'disk_pool': DISK_POOL}]

    _run_guest(GUEST_USERID, IMAGE_PATH, IMAGE_OS_VERSION, GUEST_PROFILE,
               GUEST_VCPUS, GUEST_MEMORY, network_info, disks_list)
