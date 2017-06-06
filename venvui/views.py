# -*- coding: utf-8 -*-

from aiohttp import web


async def index(request):
    return web.Response(text='Hello world!')


async def list_projects(request):
    project_svc = request.app['projects']

    projects = project_svc.find_projects()
    result = {p.pathname: {
        'name': p.name,
        'pathname': p.pathname,
        'fullpath': p.fullpath,
        'created_at': p.created_at.isoformat(timespec='seconds')
    } for p in projects}

    return web.json_response(result)


async def create_project(request):
    project_svc = request.app['projects']
    assert request.content_type == 'application/json'
    data = await request.json()

    project = project_svc.create_project(data['name'])

    return web.json_response({
        'name': project.name,
        'pathname': project.pathname,
        'fullpath': project.fullpath,
        'created_at': project.created_at.isoformat(sep=' ', timespec='seconds')
    })


async def get_project(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    project = project_svc.get_project(name)
    return web.json_response({
        'name': project.name,
        'pathname': project.pathname,
        'fullpath': project.fullpath,
        'created_at': project.created_at.isoformat(sep=' ', timespec='seconds')
    })


async def list_packages(request):
    package_svc = request.app['packages']

    packages = package_svc.list_packages()
    return web.json_response(packages)


async def start_deployment(request):
    project_svc = request.app['projects']
    name = request.match_info['name']

    assert request.content_type == 'application/json'
    data = await request.json()
    pkg_name = data['pkg_name']

    project = project_svc.get_project(name)
    deployment = project.deploy(pkg_name)
    return web.json_response(deployment.to_dict())


async def list_deployments(request):
    deployment_svc = request.app['deployments']

    return web.json_response(
        {'deployments': [v.to_dict() for v
                         in deployment_svc.list_deployments()]}
    )
