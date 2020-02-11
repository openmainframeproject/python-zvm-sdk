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


from zvmsdk import config
from zvmsdk import log
from zvmsdk import smtclient
from zvmsdk import utils as zvmutils


LOG = log.LOG
CONF = config.CONF

_IMAGEOPS = None


def get_imageops():
    global _IMAGEOPS
    if _IMAGEOPS is None:
        _IMAGEOPS = ImageOps()
    return _IMAGEOPS


class ImageOps(object):
    def __init__(self):
        self._smtclient = smtclient.get_smtclient()
        self._pathutils = zvmutils.PathUtils()

    def image_get_root_disk_size(self, image_name):
        return self._smtclient.image_get_root_disk_size(image_name)

    def image_import(self, image_name, url, image_meta, remote_host=None):

        return self._smtclient.image_import(image_name,
                                             url,
                                             image_meta,
                                             remote_host)

    def image_query(self, imagename=None):
        return self._smtclient.image_query(imagename)

    def image_delete(self, image_name):
        return self._smtclient.image_delete(image_name)

    def image_export(self, image_name, dest_url, remote_host=None):
        return self._smtclient.image_export(image_name, dest_url,
                                             remote_host)

    def flashimage_import(self, image_name, userid, vdev, image_meta):
        return self._smtclient.flashimage_import(image_name, userid, vdev, image_meta)

    def flashimage_query(self, image_name=None):
        return self._smtclient.flashimage_query(image_name)

    def flashimage_delete(self, image_name):
        return self._smtclient.flashimage_delete(image_name)
