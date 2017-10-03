# -*- coding: utf-8 -*-

import datetime
import logging
from pathlib import Path

import toml
from os import getenv

from venvui.utils.confgen import ConfigGenerator

logger = logging.getLogger(__name__)


class ProjectService:

    def __init__(self, project_root, deployment_svc, package_svc,
                 systemd_svc):
        self.project_root = Path(project_root)
        assert self.project_root.exists()
        assert self.project_root.is_dir()
        self.deployment_svc = deployment_svc
        self.package_svc = package_svc
        self.systemd_svc = systemd_svc

    def create_project(self, key, name):
        path = self.project_root / key
        project = Project(svc=self, path=path, key=key, name=name)
        project.create()
        return project

    def find_projects(self):
        for child in self.project_root.iterdir():
            yield Project.load_from_path(self, child)

    def get_project(self, name):
        path = self.project_root / name
        try:
            return Project.load_from_path(self, path)
        except FileNotFoundError:
            return None

    def global_variables(self):
        return {
            'HOME': getenv('HOME')
        }


class Project:
    config_filename = 'project.toml'
    venv_pathname = 'venv'
    current_venv_name = 'current'

    def __init__(self, svc, path, key, name, created_at=None,
                 config_files=None, systemd_services=None):
        self.svc = svc
        self.path = Path(path)
        self.key = key
        self.name = name
        self.created_at = created_at or datetime.datetime.utcnow()
        self.config_files = config_files or {}
        self.systemd_services = systemd_services or []

        self.venv_path = self.path / self.venv_pathname

    @classmethod
    def load_from_path(cls, svc, path):
        project_path = Path(path)
        config_file = project_path / cls.config_filename
        with open(config_file) as f:
            config = toml.load(f)
        config['path'] = path
        config['key'] = str(path.name)
        return cls(svc, **config)

    def config(self):
        return {'name': self.name,
                'created_at': self.created_at,
                'config_files': self.config_files,
                'systemd_services': self.systemd_services}

    def fullpath(self):
        return str(self.path.absolute())

    def create(self):
        logger.info("Creating project in: '%s'", self.path)
        self.path.mkdir()
        # make sub-directories
        self.venv_path.mkdir()
        self.save_config()

    def save_config(self):
        config_file = self.path / self.config_filename
        with open(config_file, 'w') as f:
            toml.dump(self.config(), f)

    def deploy(self, pkg_filename):
        pkg = self.svc.package_svc.get_package(pkg_filename)
        venv_name = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')

        def deployment_done(deployment):
            logger.warning("Deployment '%s': %s", deployment.key,
                           deployment.state)
            if deployment.state == 'failed':
                logger.error("Deployment failed, so not symlinking")
                return
            self.symlink_venv(deployment.venv_name)

        return self.svc.deployment_svc.deploy(
            self.key, self.venv_path, venv_name, pkg, deployment_done)

    def symlink_venv(self, target_venv_name):
        symlink_path = self.venv_path / self.current_venv_name
        logger.info("Will symlink: %s -> %s", self.current_venv_name,
                    target_venv_name)
        try:
            symlink_path.unlink()
        except FileNotFoundError:
            pass
        symlink_path.symlink_to(target_venv_name)

    def variables(self, include_global=True):
        vars = {}
        if include_global:
            vars = self.svc.global_variables()
        vars['PROJECT_NAME'] = self.name
        vars['PROJECT_PATH'] = self.fullpath()
        vars['PROJECT_KEY'] = self.key
        return vars

    # Services

    def add_systemd_service(self, service):
        self.systemd_services.append(service)

    def remove_systemd_service(self, service):
        self.systemd_services.remove(service)

    async def get_systemd_services(self):
        services = []
        for service in self.systemd_services:
            services.append(await self.get_systemd_service(service))
        return services

    async def get_systemd_service(self, service):
        status = await self.svc.systemd_svc.get_status(service)
        status['name'] = service
        return status

    async def execute_systemd_service_command(self, service, command):
        # TODO: test if service in service list
        result = await self.svc.systemd_svc.execute(service, command)
        return result

    # Config file

    def has_config_file(self, name):
        return name in self.config_files

    def get_config_file(self, name, generated=False):
        if name not in self.config_files:
            return None
        config_file = dict(name=name, **self.config_files[name])

        config_gen = self._config_generator(name)
        global_variables = self.variables()
        path = config_gen.resolved_path(global_variables)
        config_file['full_path'] = str(path.absolute())
        if generated:
            config_file['generated'] = config_gen.generate(global_variables)
        return config_file

    def list_config_files(self):
        return [self.get_config_file(name) for name in self.config_files]

    def add_config_file(self, name, template, path, vars):
        self.config_files[name] = dict(template=template,
                                       path=path, vars=vars)
        self.save_config()

    def change_config_file(self, name, partial):
        if 'name' in partial:
            new_name = partial.pop('name')
            self.config_files[new_name] = self.config_files.pop(name)
            name = new_name

        for key, value in partial.items():
            if key in ('template', 'vars', 'path'):
                self.config_files[name][key] = value
        self.save_config()

    def remove_config_file(self, name):
        del self.config_files[name]
        self.save_config()

    def _config_generator(self, name):
        config = self.config_files[name]
        return ConfigGenerator(name, config['template'], config['path'],
                               config['vars'])

    def generate_config_file(self, name, global_variables):
        config = self._config_generator(name)
        return config.generate(global_variables)

    def install_config_file(self, name):
        global_variables = self.variables()
        config = self._config_generator(name)
        path, config = config.install(global_variables, self.path)
        config_file = dict(name=name, **self.config_files[name])
        config_file['full_path'] = str(path.absolute())
        config_file['generated'] = config
        return config_file
