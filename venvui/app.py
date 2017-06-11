# -*- coding: utf-8 -*-

import asyncio
import logging
import logging.config
from pathlib import Path
import warnings

from aiohttp import web
import yaml

from venvui import views
from venvui.services import ProjectService
from venvui.services import PackageService
from venvui.services import DeploymentService

logger = logging.getLogger(__name__)


def main():
    config_path = Path('.') / 'config' / 'venvui.yaml'
    config = load_config(config_path)

    logging.config.dictConfig(config['logging'])
    logging.captureWarnings(True)
    logger.info('Logging configured!')


    package_svc = PackageService(package_root=config['package_path'])
    deploy_svc = DeploymentService()
    project_svc = ProjectService(project_root=config['project_path'],
                                 deployment_svc=deploy_svc,
                                 package_svc=package_svc)

    app = web.Application()
    app['config'] = config
    app['projects'] = project_svc
    app['packages'] = package_svc
    app['deployments'] = deploy_svc

    setup_routes(app)
    web.run_app(app, host=config['http_host'], port=config['http_port'])


def setup_routes(app):
    app.router.add_get('/projects', views.list_projects)
    app.router.add_post('/projects', views.create_project)
    app.router.add_get('/projects/{name}', views.get_project)
    app.router.add_post('/projects/{name}/deployments', views.start_deployment)
    app.router.add_get('/projects/{name}/deployments', views.list_project_deployments)
    app.router.add_get('/packages', views.list_packages)
    app.router.add_get('/deployments', views.list_deployments)
    app.router.add_get('/deployments/{key}', views.get_deployment)
    app.router.add_get('/deployments/{key}/log', views.get_deployment_log)


def load_config(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config
