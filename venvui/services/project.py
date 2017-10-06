# -*- coding: utf-8 -*-

import logging
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from string import Template

import toml
from os import getenv

logger = logging.getLogger(__name__)


class ProjectService:

    def __init__(self, project_root, deployment_svc, package_svc,
                 systemd_svc, config_svc):
        self.project_root = Path(project_root)
        assert self.project_root.exists()
        assert self.project_root.is_dir()
        self.deployment_svc = deployment_svc
        self.package_svc = package_svc
        self.systemd_svc = systemd_svc
        self.config_svc = config_svc

    def create_project(self, key, name):
        path = self.project_root / key
        return Project(self, path, name=name).create()

    def find_projects(self):
        for child in self.project_root.iterdir():
            try:
                yield Project(self, child).load()
            except FileNotFoundError:
                logger.warning("Cannot load project from '%s'", child,
                               exc_info=True)

    def get_project(self, key):
        try:
            return Project(self, self.project_root / key).load()
        except (NotADirectoryError, FileNotFoundError):
            logger.warning("Cannot load project '%s'", key, exc_info=True)
            return None

    def global_variables(self):
        return {
            'HOME': getenv('HOME')
        }


ProjectConfig = namedtuple(
    'ProjectConfig', 'name created_at config_files systemd_services')


class Project:
    config_filename = 'project.toml'
    venv_pathname = 'venv'
    current_venv_name = 'current'

    def __init__(self, svc, path, **config):
        self.svc = svc
        self.path = Path(path)
        self.key = self.path.name
        self.config = ProjectConfig(name=self.key,
                                    created_at=datetime.utcnow(),
                                    config_files={},
                                    systemd_services=[])
        self.config = self.config._replace(**config)
        self.config_file = self.path / self.config_filename
        self.venv_path = self.path / self.venv_pathname

    def load(self):
        logger.debug("Loading project '%s' from '%s'", self.key,
                     self.config_file)
        if not self.path.is_dir():
            raise NotADirectoryError("'%s' is not a directory" % self.path)
        if not self.config_file.exists():
            raise FileNotFoundError("File '%s' not found" % self.config_file)
        with open(self.config_file) as f:
            config = toml.load(f)
        self.config = ProjectConfig(**config)
        return self

    def create(self):
        logger.info("Creating project in: '%s'", self.path)
        self.path.mkdir()
        self.venv_path.mkdir()
        self.save_config()
        return self

    def get_config(self):
        return dict(config._asdict())

    def save_config(self):
        logger.debug("Saving project '%s' configuration to '%s'",
                     self.key, self.config_file)
        with open(self.config_file, 'w') as f:
            toml.dump(self.config._asdict(), f)

    def change_config(self, **kwargs):
        self.config._replace(**kwargs)
        self.save_config()

    # Properties

    def summary(self):
        return {
            'key': self.key,
            'name': self.name,
            'fullpath': self.fullpath,
            'created_at': self.created_at
        }

    @property
    def name(self):
        return self.config.name

    @property
    def created_at(self):
        return self.config.created_at

    @property
    def fullpath(self):
        return str(self.path.absolute())

    # ----

    def deploy(self, pkg_filename):
        pkg = self.svc.package_svc.get_package(pkg_filename)
        venv_name = datetime.utcnow().strftime('%Y%m%d-%H%M%S')

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
        vars['PROJECT_NAME'] = self.config.name
        vars['PROJECT_PATH'] = self.fullpath
        vars['PROJECT_KEY'] = self.key
        return vars

    # Services

    def add_systemd_service(self, service):
        systemd_services = list(self.config.systemd_services)
        systemd_services.append(service)
        self.change_config(systemd_services=systemd_services)

    def remove_systemd_service(self, service):
        systemd_services = list(self.config.systemd_services)
        systemd_services.remove(service)
        self.change_config(systemd_services=systemd_services)

    async def get_systemd_services(self):
        services = []
        for service in self.config.systemd_services:
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
        return name in self.config.config_files

    def get_config_file(self, name, generated=False):
        if name not in self.config.config_files:
            return None
        config_file = self.config.config_files[name]
        full_path = Path(self.interpolate_var(config_file['path'])).absolute()
        config_file = dict(name=name, full_path=str(full_path), **config_file)
        return config_file

    def list_config_files(self):
        return [self.get_config_file(name)
                for name in self.config.config_files]

    def add_config_file(self, name, template, path, variables):
        config_files = dict(self.config.config_files)
        config_files[name] = dict(template=template,
                                  path=path, variables=variables)
        self.change_config(config_files=config_files)

    def change_config_file(self, name, partial):
        config_files = dict(self.config.config_files)
        if 'name' in partial:
            new_name = partial.pop('name')
            config_files[new_name] = config_files.pop(name)
            name = new_name

        # Copy value dict
        config_files[name] = dict(config_files[name])

        for key, value in partial.items():
            if key in ('template', 'variables', 'path'):
                config_files[name][key] = value

        self.change_config(config_files=config_files)

    def remove_config_file(self, name):
        config_files = dict(self.config.config_files)
        del config_files[name]
        self.change_config(config_files=config_files)

    def interpolated_variables(self, variables):
        project_variables = self.variables()
        return {key: Template(value).substitute(project_variables)
                for key, value in variables.items()}

    def interpolate_var(self, value):
        return Template(value).substitute(self.variables())

    def install_config_file(self, name):
        config_file = self.config.config_files[name]
        full_path = Path(self.interpolate_var(config_file['path'])).absolute()
        config_file = dict(name=name, full_path=str(full_path), **config_file)
        variables = self.interpolated_variables(config_file['variables'])
        generated = self.svc.config_svc.install_file(
            config_file['template'], full_path, variables)
        config_file['generated'] = generated
        return config_file
