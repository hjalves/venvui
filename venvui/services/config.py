# -*- coding: utf-8 -*-

import jinja2


class ConfigService:

    def __init__(self):
        self.jinja_env = jinja2.Environment(
            loader=jinja2.PackageLoader('venvui', 'templates'),
            undefined=jinja2.StrictUndefined
        )

    def list_templates(self):
        return self.jinja_env.list_templates('j2')

    def preview(self, template_name):
        template = self.jinja_env.get_template(template_name)
        with open(template.filename) as f:
            return f.read()

    def generate(self, template_name, variables):
        template = self.jinja_env.get_template(template_name)
        return template.render(variables)

    def install_file(self, template_name, full_path, variables):
        rendered = self.generate(template_name, variables)
        with open(full_path, 'w') as f:
            f.write(rendered)
        return rendered
