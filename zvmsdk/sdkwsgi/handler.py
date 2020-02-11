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

import routes
import webob

from zvmsdk import exception
from zvmsdk import log
from zvmsdk.sdkwsgi import util
from zvmsdk.sdkwsgi.handlers import file
from zvmsdk.sdkwsgi.handlers import guest
from zvmsdk.sdkwsgi.handlers import host
from zvmsdk.sdkwsgi.handlers import image
from zvmsdk.sdkwsgi.handlers import tokens
from zvmsdk.sdkwsgi.handlers import version
from zvmsdk.sdkwsgi.handlers import volume
from zvmsdk.sdkwsgi.handlers import vswitch


LOG = log.LOG


# This is the route of zvm sdk REST API, in order to add or modify
# you need add code in handlers/ folder to handle the request
ROUTE_LIST = (
    ('/', {
        'GET': version.version,
    }),
    ('/guests', {
        'POST': guest.guest_create,
        'GET': guest.guest_list,
    }),
    ('/guests/stats', {
        'GET': guest.guest_get_stats
    }),
    ('/guests/interfacestats', {
        'GET': guest.guest_get_interface_stats
    }),
    ('/guests/nics', {
        'GET': guest.guests_get_nic_info
    }),
    ('/guests/volumes', {
        'POST': volume.volume_attach,
        'DELETE': volume.volume_detach,
    }),
    ('/volumes/conn/{userid}', {
        'GET': volume.get_volume_connector,
    }),
    ('/guests/{userid}', {
        'DELETE': guest.guest_delete,
        'GET': guest.guest_get,
    }),
    ('/guests/{userid}/action', {
        'POST': guest.guest_action,
    }),
    ('/guests/{userid}/info', {
        'GET': guest.guest_get_info,
    }),
    ('/guests/{userid}/nic', {
        'POST': guest.guest_create_nic,
    }),
    ('/guests/{userid}/nic/{vdev}', {
        'DELETE': guest.guest_delete_nic,
        'PUT': guest.guest_couple_uncouple_nic,
    }),
    ('/guests/{userid}/interface', {
        'POST': guest.guest_create_network_interface,
        'DELETE': guest.guest_delete_network_interface,
    }),
    ('/guests/{userid}/power_state', {
        'GET': guest.guest_get_power_state,
    }),
    ('/guests/{userid}/disks', {
        'POST': guest.guest_create_disks,
        'DELETE': guest.guest_delete_disks,
        'PUT': guest.guest_config_disks,
    }),
    ('/host', {
        'GET': host.host_get_info,
    }),
    ('/host/diskpool', {
        'GET': host.host_get_disk_info,
    }),
    ('/images', {
        'POST': image.image_create,
        'GET': image.image_query
    }),
    ('/images/{name}', {
        'DELETE': image.image_delete,
        'PUT': image.image_export,
    }),
    ('/images/{name}/root_disk_size', {
        'GET': image.image_get_root_disk_size,
    }),
    ('/flashimages', {
        'POST': image.flashimage_create,
        'GET': image.flashimage_query
    }),
    ('/flashimages/{name}', {
        'DELETE': image.flashimage_delete
    }), 
    ('/files', {
        'PUT': file.file_import,
        'POST': file.file_export,
    }),
    ('/token', {
        'POST': tokens.create,
    }),
    ('/vswitches', {
        'GET': vswitch.vswitch_list,
        'POST': vswitch.vswitch_create,
    }),
    ('/vswitches/{name}', {
        'GET': vswitch.vswitch_query,
        'DELETE': vswitch.vswitch_delete,
        'PUT': vswitch.vswitch_update,
    }),
)


def dispatch(environ, start_response, mapper):
    """Find a matching route for the current request.

    :raises: 404(not found) if no match request
             405(method not allowed) if route exist but
                method not provided.
    """
    result = mapper.match(environ=environ)
    if result is None:
        info = environ.get('PATH_INFO', '')
        LOG.debug('The route for %s can not be found', info)
        raise webob.exc.HTTPNotFound(
            json_formatter=util.json_error_formatter)

    handler = result.pop('action')

    environ['wsgiorg.routing_args'] = ((), result)
    return handler(environ, start_response)


def handle_not_allowed(environ, start_response):
    """Return a 405 response when method is not allowed.

    If _methods are in routing_args, send an allow header listing
    the methods that are possible on the provided URL.
    """
    _methods = util.wsgi_path_item(environ, '_methods')
    headers = {}
    if _methods:
        headers['allow'] = str(_methods)
    raise webob.exc.HTTPMethodNotAllowed(
        ('The method specified is not allowed for this resource.'),
        headers=headers, json_formatter=util.json_error_formatter)


def make_map(declarations):
    """Process route declarations to create a Route Mapper."""
    mapper = routes.Mapper()
    for route, methods in ROUTE_LIST:
        allowed_methods = []
        for method, func in methods.items():
            mapper.connect(route, action=func,
                           conditions=dict(method=[method]))
            allowed_methods.append(method)
        allowed_methods = ', '.join(allowed_methods)
        mapper.connect(route, action=handle_not_allowed,
                       _methods=allowed_methods)
    return mapper


class SdkHandler(object):
    """Serve zvm sdk request

    Dispatch to handlers defined in ROUTE_LIST.
    """

    def __init__(self, **local_config):
        self._map = make_map(ROUTE_LIST)

    def __call__(self, environ, start_response):
        clen = environ.get('CONTENT_LENGTH')
        try:
            if clen and (int(clen) > 0) and not environ.get('CONTENT_TYPE'):
                msg = 'content-type header required when content-length > 0'
                LOG.debug(msg)
                raise webob.exc.HTTPBadRequest(msg,
                   json_formatter=util.json_error_formatter)
        except ValueError:
            msg = 'content-length header must be an integer'
            LOG.debug(msg)
            raise webob.exc.HTTPBadRequest(msg,
                json_formatter=util.json_error_formatter)
        try:
            return dispatch(environ, start_response, self._map)
        except exception.NotFound as exc:
            raise webob.exc.HTTPNotFound(
                exc, json_formatter=util.json_error_formatter)
        except Exception:
            raise
