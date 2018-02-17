# -*- coding: utf-8 -*-

import asyncio
import argparse
import logging
import logging.config
from pathlib import Path
import warnings
from time import time

import aiohttp_cors
from aiohttp import web
import toml

from venvui import views
from venvui.services import ConfigService
from venvui.services import ProjectService
from venvui.services import PackageService
from venvui.services import DeploymentService
from venvui.services import SystemdManager
from venvui.services import LogViewService
from venvui.utils.misc import json_error

logger = logging.getLogger(__name__)

here_path = Path(__file__).parent

def main(args=None):
    parser = argparse.ArgumentParser(
        description='VENVUI - Manage your projects and virtual environments.')
    parser.add_argument('-c', '--config', required=True,
                        type=argparse.FileType('r'),
                        help='Configuration file')
    args = parser.parse_args(args)
    return app(config_file=args.config)


def app(config_file):
    config = load_config(config_file)

    logging.config.dictConfig(config['logging'])
    logging.captureWarnings(True)
    logger.info('Logging configured!')

    logview_svc = LogViewService()
    configfile_svc = ConfigService()
    package_svc = PackageService(package_root=config['package_path'],
                                 temp_path=config['temp_path'])
    deploy_svc = DeploymentService(temp_path=config['temp_path'],
                                   logs_path=config['logs_path'])
    systemd_svc = SystemdManager(logview_svc=logview_svc)
    project_svc = ProjectService(project_root=config['project_path'],
                                 deployment_svc=deploy_svc,
                                 package_svc=package_svc,
                                 systemd_svc=systemd_svc,
                                 config_svc=configfile_svc)

    subapp = web.Application(middlewares=[timer_middleware, error_middleware],
                             debug=config['debug_mode'],
                             logger=logging.getLogger('venvui.access'))

    subapp['config'] = config
    subapp['configfile'] = configfile_svc
    subapp['logview'] = logview_svc
    subapp['projects'] = project_svc
    subapp['packages'] = package_svc
    subapp['deployments'] = deploy_svc
    subapp['systemd'] = systemd_svc

    cors = aiohttp_cors.setup(subapp, defaults={
        "*": aiohttp_cors.ResourceOptions(allow_credentials=True,
                                          allow_headers='*',
                                          allow_methods='*'),
    })

    static = here_path / 'frontend'

    setup_routes(subapp, cors)

    app = web.Application()
    app.add_subapp('/api', subapp)

    async def index(request):
        return web.FileResponse(static / 'index.html')

    app.router.add_get('/', index)
    app.router.add_static('/', static)

    web.run_app(app, host=config['http_host'], port=config['http_port'])


def setup_routes(app, cors, prefix=''):

    def route(path, get=None, post=None, put=None, delete=None):
        resource = cors.add(app.router.add_resource(prefix + path))
        if get:
            resource.add_route('GET', get)
        if post:
            resource.add_route('POST', post)
        if put:
            resource.add_route('PUT', put)
        if delete:
            resource.add_route('DELETE', delete)

    route('/projects',
          get=views.list_projects,
          post=views.create_project)
    route('/projects/{key}',
          get=views.get_project)
    route('/projects/{key}/deployments',
          get=views.list_project_deployments,
          post=views.start_deployment)
    route('/projects/{key}/configs',
          get=views.get_config_files,
          post=views.add_config_file)
    route('/projects/{key}/configs/{config}',
          get=views.get_config_file,
          put=views.change_config_file,
          delete=views.remove_config_file)
    route('/projects/{key}/configs/{config}/install',
          post=views.install_config_file)
    route('/projects/{key}/services',
          get=views.get_project_services,
          post=views.add_service)
    route('/projects/{key}/services/{service}',
          get=views.get_project_service,
          delete=views.delete_service)
    route('/projects/{key}/services/{service}/{command}',
          post=views.project_service_execute_command)
    route('/packages',
          get=views.list_packages,
          post=views.upload_package)
    route('/packages/{filename}',
          get=views.get_package)
    route('/deployments',
          get=views.list_deployments)
    route('/deployments/{key}',
          get=views.get_deployment)
    route('/deployments/{key}/log',
          get=views.get_deployment_log)
    route('/services',
          get=views.list_services)
    route('/services/{service}',
          get=views.get_service)
    route('/services/{service}/log',
          get=views.get_service_log)
    #route('/services/{service}/{command}',
    #      post=views.service_execute_command)


@web.middleware
async def timer_middleware(request, handler):
    now = time()
    response = await handler(request)
    elapsed = (time() - now) * 1000
    timer_logger = logger.getChild('timer')
    timer_logger.log(logging.DEBUG if elapsed <= 100 else logging.WARNING,
                     "%s: %.3f ms", request.rel_url, elapsed)
    if response and not response.prepared:
        response.headers['X-Elapsed'] = "%.3f ms" % elapsed
    return response


@web.middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
        if response and response.status >= 400:
            return json_error(response.reason, response.status)
        return response
    except web.HTTPException as ex:
        if ex.status >= 400:
            return json_error(ex.reason, ex.status)
        raise
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Exception while handling request %s:",
                         request.rel_url)
        return json_error('%s: %s' % (e.__class__.__name__, e), 500)


def load_config(file):
    if isinstance(file, (str, Path)):
        file = open(file)
    with file:
        config = toml.load(file)
    return config
