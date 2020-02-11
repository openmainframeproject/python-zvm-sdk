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

"""Handler for the image of the sdk API."""
import json

from zvmconnector import connector
from zvmsdk import config
from zvmsdk import log
from zvmsdk import utils
from zvmsdk.sdkwsgi.handlers import tokens
from zvmsdk.sdkwsgi.schemas import image
from zvmsdk.sdkwsgi import util
from zvmsdk.sdkwsgi import validation


_IMAGEACTION = None
CONF = config.CONF
LOG = log.LOG


class ImageAction(object):

    def __init__(self):
        self.client = connector.ZVMConnector(connection_type='socket',
                                             ip_addr=CONF.sdkserver.bind_addr,
                                             port=CONF.sdkserver.bind_port)

    @validation.schema(image.create)
    def create(self, body):
        image = body['image']
        image_name = image['image_name']
        url = image['url']
        remote_host = image.get('remote_host', None)
        image_meta = image['image_meta']

        info = self.client.send_request('image_import', image_name,
                                        url, image_meta, remote_host)
        return info

    @validation.query_schema(image.query)
    def get_root_disk_size(self, req, name):
        # FIXME: this param need combined image nameg, e.g the profile
        # name, not the given image name from customer side
        info = self.client.send_request('image_get_root_disk_size',
                                        name)
        return info

    def delete(self, name):
        info = self.client.send_request('image_delete', name)
        return info

    @validation.query_schema(image.query)
    def query(self, req, name):
        info = self.client.send_request('image_query', name)
        return info

    @validation.schema(image.export)
    def export(self, name, body):
        location = body['location']
        dest_url = location['dest_url']
        remotehost = location.get('remote_host', None)
        info = self.client.send_request('image_export', name,
                                        dest_url, remotehost)
        return info

#    @validation.schema(image.flash_create)
    def flash_create(self, body):
        image = body['image']
        image_name = image['image_name']
        userid = image['userid']
        vdev = image['vdev']
        image_meta = image['image_meta']
        info = self.client.send_request('flashimage_import', image_name,
                                        userid, vdev, image_meta)
        return info

    def flash_query(self, req, name):
        info = self.client.send_request('flashimage_query', name)
        return info

    def flash_delete(self, name):
        info = self.client.send_request('flashimage_delete', name)
        return info


def get_action():
    global _IMAGEACTION
    if _IMAGEACTION is None:
        _IMAGEACTION = ImageAction()
    return _IMAGEACTION


@util.SdkWsgify
@tokens.validate
def image_create(req):

    def _image_create(req):
        action = get_action()
        body = util.extract_json(req.body)
        return action.create(body=body)

    info = _image_create(req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler = util.handle_already_exists)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def image_get_root_disk_size(req):

    def _image_get_root_disk_size(req, name):
        action = get_action()
        return action.get_root_disk_size(req, name)

    name = util.wsgi_path_item(req.environ, 'name')
    info = _image_get_root_disk_size(req, name)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.content_type = 'application/json'
    req.response.status = util.get_http_code_from_sdk_return(info)
    return req.response


@util.SdkWsgify
@tokens.validate
def image_delete(req):

    def _image_delete(name):
        action = get_action()
        return action.delete(name)

    name = util.wsgi_path_item(req.environ, 'name')
    info = _image_delete(name)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info, default=200)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def image_export(req):

    def _image_export(name, req):
        action = get_action()
        body = util.extract_json(req.body)
        return action.export(name, body=body)

    name = util.wsgi_path_item(req.environ, 'name')
    info = _image_export(name, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler=util.handle_not_found)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def image_query(req):

    def _image_query(imagename, req):
        action = get_action()
        return action.query(req, imagename)

    imagename = None
    if 'imagename' in req.GET:
        imagename = req.GET['imagename']
    info = _image_query(imagename, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler = util.handle_not_found)
    req.response.content_type = 'application/json'
    return req.response

@util.SdkWsgify
@tokens.validate
def flashimage_query(req):

    def _image_query(imagename, req):
        action = get_action()
        return action.flash_query(req, imagename)

    imagename = None
    if 'imagename' in req.GET:
        imagename = req.GET['imagename']
    info = _image_query(imagename, req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler = util.handle_not_found)
    req.response.content_type = 'application/json'
    return req.response

@util.SdkWsgify
@tokens.validate
def flashimage_create(req):

    def _image_create(req):
        action = get_action()
        body = util.extract_json(req.body)
        return action.flash_create(body=body)

    info = _image_create(req)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info,
        additional_handler = util.handle_already_exists)
    req.response.content_type = 'application/json'
    return req.response


@util.SdkWsgify
@tokens.validate
def flashimage_delete(req):

    def _image_delete(name):
        action = get_action()
        return action.flash_delete(name)

    name = util.wsgi_path_item(req.environ, 'name')
    info = _image_delete(name)

    info_json = json.dumps(info)
    req.response.body = utils.to_utf8(info_json)
    req.response.status = util.get_http_code_from_sdk_return(info, default=200)
    req.response.content_type = 'application/json'
    return req.response
