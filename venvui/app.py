# -*- coding: utf-8 -*-

import asyncio
import logging
import logging.config
from pathlib import Path
import warnings
from time import time

import aiohttp_cors
from aiohttp import web
import toml

from venvui import views
from venvui.services import ProjectService
from venvui.services import PackageService
from venvui.services import DeploymentService
from venvui.services import SystemdManager
from venvui.utils.misc import json_error

logger = logging.getLogger(__name__)


def main():
    config_path = Path('.') / 'config' / 'venvui.toml'
    config = load_config(config_path)

    logging.config.dictConfig(config['logging'])
    logging.captureWarnings(True)
    logger.info('Logging configured!')


    package_svc = PackageService(package_root=config['package_path'],
                                 temp_path=config['temp_path'])
    deploy_svc = DeploymentService(temp_path=config['temp_path'],
                                   logs_path=config['logs_path'])
    systemd_svc = SystemdManager()
    project_svc = ProjectService(project_root=config['project_path'],
                                 deployment_svc=deploy_svc,
                                 package_svc=package_svc,
                                 systemd_svc=systemd_svc)

    app = web.Application(middlewares=[timer_middleware, error_middleware],
                          debug=config['debug_mode'])
    app['config'] = config
    app['projects'] = project_svc
    app['packages'] = package_svc
    app['deployments'] = deploy_svc
    app['systemd'] = systemd_svc

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(allow_credentials=True,
                                          allow_headers='*',
                                          allow_methods='*'),
    })

    setup_routes(app, cors)
    web.run_app(app, host=config['http_host'], port=config['http_port'])


def setup_routes(app, cors):

    def route(path, get=None, post=None, put=None, delete=None):
        resource = cors.add(app.router.add_resource(path))
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
          get=views.get_services,
          post=views.add_service)
    route('/projects/{key}/services/{service}',
          get=views.get_service,
          delete=views.delete_service)
    route('/projects/{key}/services/{service}/{command}',
          get=views.service_execute_command)
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


async def timer_middleware(app, handler):
    async def middleware_handler(request):
        now = time()
        response = await handler(request)
        elapsed = (time() - now) * 1000
        timer_logger = logger.getChild('timer')
        timer_logger.log(logging.DEBUG if elapsed <= 100 else logging.WARNING,
                         "%s: %.3f ms", request.rel_url, elapsed)
        if response and not response.prepared:
            response.headers['X-Elapsed'] = "%.3f ms" % elapsed
        return response
    return middleware_handler


async def error_middleware(app, handler):
    async def middleware_handler(request):
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
    return middleware_handler


def load_config(path):
    with open(path) as f:
        config = toml.load(f)
    return config
