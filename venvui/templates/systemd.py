# -*- coding: utf-8 -*-


TEMPLATE = """[Unit]
Description={description}

[Service]
Type=simple
ExecStart={execstart}
WorkingDirectory={workingdir}

[Install]
WantedBy=default.target
"""


def gen_config(description, execstart, workingdir):
    return TEMPLATE.format(description=description,
                           execstart=execstart,
                           workingdir=workingdir)
