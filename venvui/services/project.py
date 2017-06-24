# -*- coding: utf-8 -*-

import datetime
import logging
from pathlib import Path

import yaml

from venvui.utils.confgen import ConfigGenerator

logger = logging.getLogger(__name__)


class ProjectService:

    def __init__(self, project_root, deployment_svc, package_svc):
        self.project_root = Path(project_root)
        assert self.project_root.exists()
        assert self.project_root.is_dir()
        self.deployment_svc = deployment_svc
        self.package_svc = package_svc

    def create_project(self, name):
        path = self.project_root / name
        project = Project(svc=self, path=path, name=name)
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


class Project:
    config_filename = 'project.yaml'
    venv_pathname = 'venv'

    def __init__(self, svc, path, name, created_at=None, config_files=None):
        self.svc = svc
        self.path = Path(path)
        self.name = name
        self.created_at = created_at or datetime.datetime.utcnow()
        self.config_files = config_files or {}

    @classmethod
    def load_from_path(cls, svc, path):
        config_file = Path(path) / cls.config_filename
        with open(config_file) as f:
            config = yaml.safe_load(f)
            config['path'] = path
            return cls(svc, **config)

    @property
    def config(self):
        return {'name': self.name,
                'created_at': self.created_at,
                'config_files': self.config_files}

    @property
    def pathname(self):
        return str(self.path.name)

    @property
    def fullpath(self):
        return str(self.path.absolute())

    def create(self):
        logger.info("Creating project in: '%s'", self.path)
        self.path.mkdir()
        # make sub-directories
        venv_path = self.path / self.venv_pathname
        venv_path.mkdir()
        self.save_config()

    def save_config(self):
        config_file = self.path / self.config_filename
        with open(config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def deploy(self, pkg_name):
        pkg = self.svc.package_svc.get_package(pkg_name)
        venv_time = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        venv_name = '{}-{}-{}'.format(pkg['name'], pkg['version'], venv_time)
        venv_root = self.path / self.venv_pathname
        return self.svc.deployment_svc.deploy(
            self.name, venv_root, venv_name, pkg)

    # Configuration files

    def add_config_file(self, name, template, path, **vars):
        self.config_files[name] = dict(template=template,
                                       path=path, **vars)
        self.save_config()

    def change_config_file(self, name, key, value):
        self.config_files[name][key] = value
        self.save_config()

    def remove_config_file(self, name):
        del self.config_files[name]
        self.save_config()

    def _config_generator(self, name):
        variables = dict(self.config_files[name])
        template = variables.pop('template')
        path = variables.pop('path')
        return ConfigGenerator(name, template, path, variables)

    def generate_config_file(self, name, global_variables):
        config = self._config_generator(name)
        return config.generate(global_variables)

    def install_config_file(self, name, global_variables):
        config = self._config_generator(name)
        return config.install(global_variables)
