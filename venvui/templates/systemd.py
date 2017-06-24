# -*- coding: utf-8 -*-


TEMPLATE = """[Unit]
Description={description}

[Service]
ExecStart={execstart}

[Install]
WantedBy=default.target
"""


def gen_config(description, execstart):
    return TEMPLATE.format(description=description, execstart=execstart)
