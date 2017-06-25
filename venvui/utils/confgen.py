# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

from string import Template
from pathlib import Path

from venvui.templates import systemd


class ConfigGenerator:
    available_templates = {
        'systemd': systemd.gen_config
    }

    def __init__(self, name, template, path, variables):
        self.name = name
        self.template = template
        self.path = path
        self.variables = variables

    @staticmethod
    def interpolate_var(value, global_variables):
        return Template(value).substitute(global_variables)

    def install(self, global_variables, config_root):
        path = self.resolved_path(global_variables, config_root)
        config = self.generate(global_variables)
        with path.open('w') as f:
            f.write(config)
        return path, config

    def resolved_path(self, global_variables, config_root=None):
        path = Path(self.interpolate_var(self.path, global_variables))
        if config_root:
            config_root = Path(config_root)
            path = config_root.joinpath(path)
        return path

    def generate(self, global_variables):
        template_gen = self.available_templates[self.template]
        variables = {key: self.interpolate_var(value, global_variables)
                     for key, value in self.variables.items()}
        return template_gen(**variables)

