# -*- coding: utf-8 -*-


from aiohttp import web
from aiohttp.web_response import StreamResponse

from venvui.utils.misc import jsonify, jsonbody


async def list_projects(request):
    project_svc = request.app['projects']

    projects = project_svc.find_projects()
    result = {p.pathname: {
        'name': p.name,
        'pathname': p.pathname,
        'fullpath': p.fullpath,
        'created_at': p.created_at
    } for p in projects}

    return jsonify(result)


async def create_project(request):
    project_svc = request.app['projects']
    data = await jsonbody(request)

    project = project_svc.create_project(data['name'])

    return jsonify({
        'name': project.name,
        'pathname': project.pathname,
        'fullpath': project.fullpath,
        'created_at': project.created_at
    })


async def get_project(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")

    return jsonify({
        'name': project.name,
        'pathname': project.pathname,
        'fullpath': project.fullpath,
        'created_at': project.created_at
    })


async def list_packages(request):
    package_svc = request.app['packages']

    packages = package_svc.list_packages()
    return jsonify(packages)


async def upload_package(request):
    package_svc = request.app['packages']
    saved = []
    multipart = await request.multipart()

    async for part in multipart:
        if part.filename:
            pkg = await package_svc.save_package_from_part(part)
            saved.append(pkg)
    return jsonify(saved=saved)


async def start_deployment(request):
    project_svc = request.app['projects']
    name = request.match_info['name']

    data = await jsonbody(request)
    pkg_name = data['pkg_name']

    project = project_svc.get_project(name)
    deployment = project.deploy(pkg_name)
    return jsonify(deployment.to_dict())


async def list_deployments(request):
    deployment_svc = request.app['deployments']

    deployments = [v.to_dict() for v in deployment_svc.list_deployments()]
    return jsonify(deployments=deployments)


async def list_project_deployments(request):
    deployment_svc = request.app['deployments']
    project_name = request.match_info['name']

    deployment_list = deployment_svc.list_deployments(project_name)
    deployments = [v.to_dict() for v in deployment_list]
    return jsonify(deployments=deployments)


async def get_deployment(request):
    deployment_svc = request.app['deployments']
    key = request.match_info['key']

    deployment = deployment_svc.get_deployment(key)

    return jsonify(deployment.to_dict())


async def get_deployment_log(request):
    deployment_svc = request.app['deployments']
    key = request.match_info['key']

    deployment = deployment_svc.get_deployment(key)

    response = StreamResponse(status=200, reason='OK')
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    await response.prepare(request)

    async for timestamp, channel, line in deployment.log():
        text = '%s|%s|%s\n' % (timestamp.isoformat(), channel, line)
        response.write(text.encode('utf-8'))

    return response


async def get_config_files(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")
    return jsonify(configs=project.list_config_files())


async def get_config_file(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    config_name = request.match_info['config']
    generated = 'generate' in request.query

    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")
    config = project.get_config_file(config_name, generated)
    if not config:
        raise web.HTTPNotFound(reason="Config file not found")
    return jsonify(config)


async def add_config_file(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")

    data = await jsonbody(request)
    project.add_config_file(data['name'], data['template'], data['path'],
                            data['vars'])
    config = project.get_config_file(data['name'])
    return jsonify(config)


async def change_config_file(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    config_name = request.match_info['config']
    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")
    if not project.has_config_file(config_name):
        raise web.HTTPNotFound(reason="Config file not found")
    data = await jsonbody(request)
    project.change_config_file(config_name, data)
    if 'name' in data:
        config_name = data['name']
    config = project.get_config_file(config_name)
    return jsonify(config)


async def remove_config_file(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    config_name = request.match_info['config']
    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")
    if not project.has_config_file(config_name):
        raise web.HTTPNotFound(reason="Config file not found")
    project.remove_config_file(config_name)
    return web.HTTPNoContent()


async def install_config_file(request):
    project_svc = request.app['projects']
    name = request.match_info['name']
    config_name = request.match_info['config']
    project = project_svc.get_project(name)
    if not project:
        raise web.HTTPNotFound(reason="Project not found")

    config = project.install_config_file(config_name)
    return jsonify(config)
